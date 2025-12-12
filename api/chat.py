from http.server import BaseHTTPRequestHandler
import json
import os
import traceback

# משתנה גלובלי לשמירת שגיאות טעינה
STARTUP_ERROR = None

try:
    # מנסים לטעון ספריות. אם נכשל - שומרים את השגיאה ולא קורסים.
    from openai import OpenAI
    from woocommerce import API
except Exception as e:
    STARTUP_ERROR = f"Library Import Failed: {str(e)}"

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # 1. שליחת כותרות הצלחה מיד (כדי למנוע שגיאת תקשורת בדפדפן)
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        # 2. אם הייתה שגיאה בטעינת הספריות - מדווחים עליה ועוצרים
        if STARTUP_ERROR:
            self.wfile.write(json.dumps({
                "error": "Server Startup Error", 
                "details": STARTUP_ERROR,
                "hint": "Check requirements.txt"
            }).encode('utf-8'))
            return

        try:
            # 3. קריאת המידע מהדפדפן
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            
            user_msg = data.get('message')
            thread_id = data.get('thread_id')
            
            # 4. בדיקת מפתחות
            api_key = os.environ.get("OPENAI_API_KEY")
            assistant_id = os.environ.get("OPENAI_ASSISTANT_ID")
            
            if not api_key:
                raise Exception("Missing OPENAI_API_KEY env var")
            if not assistant_id:
                raise Exception("Missing OPENAI_ASSISTANT_ID env var")

            # 5. אתחול OpenAI
            client = OpenAI(api_key=api_key)

            # ניהול שיחה
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

            # 6. לולאת המתנה (Polling)
            import time
            start_time = time.time()
            
            while True:
                # הגנה מזמן ריצה (55 שניות)
                if time.time() - start_time > 55:
                    raise Exception("Timeout: OpenAI took too long (>55s)")

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
                    # טיפול בכלים (פונקציות)
                    tool_calls = run_status.required_action.submit_tool_outputs.tool_calls
                    
                    # נכין את המשתנים ללוגיקה
                    final_reply = None
                    action_payload = None

                    for tool in tool_calls:
                        func_name = tool.function.name
                        args = json.loads(tool.function.arguments)

                        if func_name == "show_products":
                            # אתחול ווקומרס מוגן
                            try:
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
                                    woo_res = wcapi.get("products", params={"include": ids_str})
                                    if woo_res.status_code == 200:
                                        for p in woo_res.json():
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
                            except Exception as woo_err:
                                print(f"Woo Error: {woo_err}")

                            # הכנת תשובה
                            client.beta.threads.runs.cancel(thread_id=thread_id, run_id=run.id)
                            final_reply = "מצאתי את המוצרים הבאים:"
                            action_payload = {
                                "action": "show_products", 
                                "products": products_data
                            }
                            break # מספיק כלי אחד

                    # שליחת תשובה סופית אם יש
                    if final_reply:
                        response = {
                            "reply": final_reply,
                            "thread_id": thread_id
                        }
                        if action_payload:
                            response.update(action_payload)
                        
                        self.wfile.write(json.dumps(response).encode('utf-8'))
                        break

                elif run_status.status in ['failed', 'cancelled', 'expired']:
                    err_msg = f"OpenAI Run Failed: {run_status.last_error}"
                    raise Exception(err_msg)
                
                time.sleep(0.5)

        except Exception as e:
            # תפיסת כל שגיאה והדפסתה ללקוח
            error_msg = str(e)
            trace = traceback.format_exc()
            print(f"CRITICAL ERROR: {trace}")
            
            self.wfile.write(json.dumps({
                "error": "Internal Error",
                "message": error_msg,
                "trace": trace
            }).encode('utf-8'))
