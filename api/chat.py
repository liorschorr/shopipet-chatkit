from http.server import BaseHTTPRequestHandler
import json
import os
import time
import traceback

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # 1. קודם כל מחזירים 200 כדי שהדפדפן לא יחשוב שהשרת מת
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        try:
            # --- שלב א': טעינת ספריות בטוחה (Lazy Loading) ---
            try:
                from openai import OpenAI
                from woocommerce import API
            except ImportError as e:
                raise Exception(f"CRITICAL: Libraries missing. {e}")

            # קריאת תוכן ההודעה
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            
            user_msg = data.get('message')
            thread_id = data.get('thread_id')
            
            # בדיקת משתני סביבה
            api_key = os.environ.get("OPENAI_API_KEY")
            assistant_id = os.environ.get("OPENAI_ASSISTANT_ID")
            if not api_key or not assistant_id:
                raise Exception("Missing API Keys configuration")

            # אתחול OpenAI
            client = OpenAI(api_key=api_key)

            # 2. ניהול ה-Thread
            if not thread_id:
                thread = client.beta.threads.create()
                thread_id = thread.id
            
            # 3. שליחת ההודעה ל-OpenAI
            client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=user_msg
            )

            # 4. הרצת ה-Assistant
            run = client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=assistant_id
            )

            # 5. לולאת המתנה (Polling)
            start_time = time.time()
            while True:
                # הגנה מפני Timeout של Vercel (אם עוברות 50 שניות)
                if time.time() - start_time > 50:
                    raise Exception("Timeout: OpenAI took too long to respond")

                run_status = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
                
                if run_status.status == 'completed':
                    messages = client.beta.threads.messages.list(thread_id=thread_id)
                    reply = messages.data[0].content[0].text.value
                    
                    # ניקוי הערות שוליים
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

                        # --- מקרה: הצגת מוצרים (UI) ---
                        if func_name == "show_products":
                            # אתחול ווקומרס רק כשצריך
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
                                # המרת ה-IDs למחרוזת
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
                                except Exception as e:
                                    print(f"Woo Error: {e}")

                            # ביטול הריצה כדי שהבוט לא יכתוב טקסט, ושליחת הנתונים לקליינט
                            client.beta.threads.runs.cancel(thread_id=thread_id, run_id=run.id)
                            
                            response_payload["reply"] = "הנה המוצרים שמצאתי:" 
                            response_payload["action"] = "show_products"
                            response_payload["products"] = products_data
                            
                            self.wfile.write(json.dumps(response_payload).encode('utf-8'))
                            should_break = True
                            break # יוצאים מלולאת הכלים

                        # --- מקרה: בדיקת הזמנה ---
                        elif func_name == "check_order":
                            # כאן נוסיף את הלוגיקה בהמשך
                            tool_outputs.append({
                                "tool_call_id": tool.id,
                                "output": json.dumps({"status": "not_found", "message": "Demo"})
                            })

                    if should_break:
                        break

                    # הגשת תוצאות לכלים אחרים
                    if tool_outputs:
                        client.beta.threads.runs.submit_tool_outputs(
                            thread_id=thread_id,
                            run_id=run.id,
                            tool_outputs=tool_outputs
                        )

                elif run_status.status in ['failed', 'cancelled', 'expired']:
                    err_msg = f"Run failed with status: {run_status.status}"
                    if run_status.last_error:
                        err_msg += f" ({run_status.last_error.message})"
                    raise Exception(err_msg)
                
                time.sleep(0.5)

        except Exception as e:
            # תפיסת כל שגיאה והדפסתה ללוג וללקוח
            print(f"CHAT ERROR: {traceback.format_exc()}")
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
