from http.server import BaseHTTPRequestHandler
import json
import os
import time
import traceback

# --- אתחול גלובלי מוגן ---
INIT_ERROR = None
try:
    from openai import OpenAI
    from woocommerce import API
except Exception as e:
    INIT_ERROR = f"Import Error: {str(e)}"

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # 1. שליחת כותרות הצלחה מיד (כדי למנוע שגיאת תקשורת בדפדפן)
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        # אם הייתה שגיאה בטעינת הספריות, נחזיר אותה עכשיו
        if INIT_ERROR:
            self.wfile.write(json.dumps({"error": INIT_ERROR}).encode('utf-8'))
            return

        try:
            # 2. קריאת המידע מהדפדפן
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            
            user_msg = data.get('message')
            thread_id = data.get('thread_id')
            
            # 3. בדיקת מפתחות
            api_key = os.environ.get("OPENAI_API_KEY")
            assistant_id = os.environ.get("OPENAI_ASSISTANT_ID")
            
            if not api_key or not assistant_id:
                raise Exception("Missing API Keys in Vercel Settings")

            # 4. התחלה
            client = OpenAI(api_key=api_key)

            if not thread_id:
                thread = client.beta.threads.create()
                thread_id = thread.id
            
            client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=user_msg
            )

            run = client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=assistant_id
            )

            # 5. לולאת המתנה
            start_time = time.time()
            while True:
                # הגנה מזמן ריצה ארוך
                if time.time() - start_time > 55:
                    raise Exception("Timeout: OpenAI took too long")

                run_status = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
                
                if run_status.status == 'completed':
                    messages = client.beta.threads.messages.list(thread_id=thread_id)
                    reply = messages.data[0].content[0].text.value
                    
                    # ניקוי
                    import re
                    reply = re.sub(r'【.*?†source】', '', reply)
                    
                    self.wfile.write(json.dumps({
                        "reply": reply, 
                        "thread_id": thread_id
                    }).encode('utf-8'))
                    break
                
                elif run_status.status == 'requires_action':
                    tool_calls = run_status.required_action.submit_tool_outputs.tool_calls
                    tool_outputs = []
                    response_payload = {"thread_id": thread_id}
                    should_break = False

                    for tool in tool_calls:
                        func_name = tool.function.name
                        args = json.loads(tool.function.arguments)

                        # --- טיפול במוצרים (UI) ---
                        if func_name == "show_products":
                            # אתחול ווקומרס
                            wcapi = API(
                                url=os.environ.get("WOO_BASE_URL"),
                                consumer_key=os.environ.get("WOO_CONSUMER_KEY"),
                                consumer_secret=os.environ.get("WOO_CONSUMER_SECRET"),
                                version="wc/v3",
                                timeout=20
                            )

                            product_ids = args.get("product_ids", [])
                            products_data = []
                            
                            if product_ids:
                                ids_str = ",".join(map(str, product_ids))
                                try:
                                    woo_res = wcapi.get("products", params={"include": ids_str})
                                    if woo_res.status_code == 200:
                                        raw_products = woo_res.json()
                                        for p in raw_products:
                                            products_data.append({
                                                "id": p['id'],
                                                "name": p['name'],
                                                "price": f"{p['price']} ₪",
                                                "regular_price": f"{p['regular_price']} ₪",
                                                "sale_price": f"{p['sale_price']} ₪",
                                                "on_sale": p['on_sale'],
                                                "image": p['images'][0]['src'] if p['images'] else "",
                                                "permalink": p['permalink'],
                                                "add_to_cart_url": f"{os.environ.get('WOO_BASE_URL')}/?add-to-cart={p['id']}"
                                            })
                                except Exception as w_err:
                                    print(f"Woo Error: {w_err}") # רק ללוגים

                            # עצירת הריצה ושליחת הנתונים
                            client.beta.threads.runs.cancel(thread_id=thread_id, run_id=run.id)
                            
                            response_payload["reply"] = "מצאתי את המוצרים הבאים:"
                            response_payload["action"] = "show_products"
                            response_payload["products"] = products_data
                            
                            self.wfile.write(json.dumps(response_payload).encode('utf-8'))
                            should_break = True
                            break

                        # --- טיפול בהזמנות ---
                        elif func_name == "check_order":
                            tool_outputs.append({
                                "tool_call_id": tool.id,
                                "output": json.dumps({"status": "error", "message": "Not implemented yet"})
                            })

                    if should_break:
                        break

                    if tool_outputs:
                        client.beta.threads.runs.submit_tool_outputs(
                            thread_id=thread_id,
                            run_id=run.id,
                            tool_outputs=tool_outputs
                        )

                elif run_status.status in ['failed', 'cancelled', 'expired']:
                    err_msg = f"Run failed: {run_status.last_error}"
                    raise Exception(err_msg)
                
                time.sleep(0.5)

        except Exception as e:
            # תפיסת כל שגיאה אפשרית והחזרתה כ-JSON
            error_details = traceback.format_exc()
            print(f"CRITICAL ERROR: {error_details}")
            self.wfile.write(json.dumps({
                "error": str(e),
                "details": "Check Vercel Logs for full traceback"
            }).encode('utf-8'))
