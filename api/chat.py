from http.server import BaseHTTPRequestHandler
import json
import os
import time
import traceback

# --- אתחול בטוח ---
try:
    from openai import OpenAI
    from woocommerce import API
except ImportError:
    OpenAI = None
    API = None

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        try:
            # 1. בדיקת ספריות
            if not OpenAI or not API:
                raise Exception("Libraries not installed. Check requirements.txt")

            # 2. קריאת מידע
            content_length = int(self.headers.get('content-length', 0))
            body = json.loads(self.rfile.read(content_length))
            user_msg = body.get('message')
            thread_id = body.get('thread_id')

            client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            assistant_id = os.environ.get("OPENAI_ASSISTANT_ID")

            # 3. ניהול שיחה
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

            # 4. לולאת המתנה (עד 50 שניות)
            start_time = time.time()
            while True:
                if time.time() - start_time > 50:
                    self.wfile.write(json.dumps({"reply": "לוקח לי זמן לחשוב... נסה שוב רגע."}).encode('utf-8'))
                    break

                run_status = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
                
                if run_status.status == 'completed':
                    # תשובה רגילה (טקסט)
                    msgs = client.beta.threads.messages.list(thread_id=thread_id)
                    reply = msgs.data[0].content[0].text.value
                    
                    # ניקוי הערות שוליים
                    import re
                    reply = re.sub(r'【.*?】', '', reply)
                    
                    self.wfile.write(json.dumps({
                        "reply": reply, 
                        "thread_id": thread_id
                    }).encode('utf-8'))
                    break
                
                elif run_status.status == 'requires_action':
                    # --- הבוט רוצה להציג מוצרים! ---
                    tool_calls = run_status.required_action.submit_tool_outputs.tool_calls
                    
                    for tool in tool_calls:
                        if tool.function.name == "show_products":
                            # 1. משיכת ה-IDs שהבוט מצא
                            args = json.loads(tool.function.arguments)
                            product_ids = args.get("product_ids", [])
                            
                            products_data = []
                            if product_ids:
                                # 2. שליפת פרטים מווקומרס
                                wcapi = API(
                                    url=os.environ.get("WOO_BASE_URL"),
                                    consumer_key=os.environ.get("WOO_CONSUMER_KEY"),
                                    consumer_secret=os.environ.get("WOO_CONSUMER_SECRET"),
                                    version="wc/v3",
                                    timeout=20
                                )
                                ids_str = ",".join(map(str, product_ids))
                                try:
                                    res = wcapi.get("products", params={"include": ids_str})
                                    if res.status_code == 200:
                                        for p in res.json():
                                            # בניית אובייקט מוצר ל-Frontend
                                            img = p['images'][0]['src'] if p['images'] else "https://placehold.co/150x150?text=No+Image"
                                            products_data.append({
                                                "id": p['id'],
                                                "name": p['name'],
                                                "price": f"{p['price']} ₪",
                                                "regular_price": f"{p['regular_price']} ₪",
                                                "sale_price": f"{p['sale_price']} ₪",
                                                "on_sale": p['on_sale'],
                                                "image": img,
                                                "permalink": p['permalink'],
                                                "add_to_cart_url": f"{os.environ.get('WOO_BASE_URL')}/?add-to-cart={p['id']}"
                                            })
                                except Exception as e:
                                    print(f"Woo Error: {e}")

                            # 3. ביטול הריצה (כדי שהבוט לא יכתוב טקסט סתם) ושליחת המוצרים
                            client.beta.threads.runs.cancel(thread_id=thread_id, run_id=run.id)
                            
                            self.wfile.write(json.dumps({
                                "action": "show_products",
                                "products": products_data,
                                "reply": "הנה המוצרים שמצאתי עבורך:", # כותרת לפני הכרטיסיות
                                "thread_id": thread_id
                            }).encode('utf-8'))
                            return # יציאה מהפונקציה

                elif run_status.status in ['failed', 'expired', 'cancelled']:
                    self.wfile.write(json.dumps({"error": "AI Error"}).encode('utf-8'))
                    break
                
                time.sleep(0.5)

        except Exception as e:
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
