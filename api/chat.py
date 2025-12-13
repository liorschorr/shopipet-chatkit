from http.server import BaseHTTPRequestHandler
import json
import os
import traceback
import time

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # 1. קודם כל שולחים 200 OK כדי שהדפדפן לא יצעק "שגיאת תקשורת"
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        # הוספת כותרות CORS ליתר ביטחון
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

        try:
            # --- שלב א: בדיקת ספריות ומשתנים ---
            try:
                from openai import OpenAI
                from woocommerce import API
            except ImportError as e:
                raise Exception(f"Import Error: {e}. Check requirements.txt")

            if not os.environ.get("OPENAI_API_KEY"):
                raise Exception("Missing OPENAI_API_KEY")

            # --- שלב ב: קריאת המידע ---
            content_length = int(self.headers.get('content-length', 0))
            if content_length == 0:
                raise Exception("No data received")
                
            post_data = self.rfile.read(content_length)
            body = json.loads(post_data)
            user_msg = body.get('message')
            thread_id = body.get('thread_id')

            # --- שלב ג: לוגיקת ה-AI ---
            client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            assistant_id = os.environ.get("OPENAI_ASSISTANT_ID")

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

            # --- שלב ד: המתנה (Polling) ---
            start_time = time.time()
            while True:
                # הגנה מזמן ריצה ארוך (55 שניות)
                if time.time() - start_time > 55:
                    self.wfile.write(json.dumps({
                        "reply": "הפעולה לקחה יותר מדי זמן (Timeout). נסה שוב.",
                        "thread_id": thread_id
                    }).encode('utf-8'))
                    return

                run_status = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
                
                if run_status.status == 'completed':
                    msgs = client.beta.threads.messages.list(thread_id=thread_id)
                    reply = msgs.data[0].content[0].text.value
                    
                    # ניקוי
                    import re
                    reply = re.sub(r'【.*?】', '', reply)
                    
                    self.wfile.write(json.dumps({
                        "reply": reply, 
                        "thread_id": thread_id
                    }).encode('utf-8'))
                    break
                
                elif run_status.status == 'requires_action':
                    # --- טיפול בכלי הצגת מוצרים ---
                    tool_calls = run_status.required_action.submit_tool_outputs.tool_calls
                    
                    for tool in tool_calls:
                        if tool.function.name == "show_products":
                            # שליפת IDs
                            args = json.loads(tool.function.arguments)
                            product_ids = args.get("product_ids", [])
                            
                            products_data = []
                            if product_ids:
                                wcapi = API(
                                    url=os.environ.get("WOO_BASE_URL"),
                                    consumer_key=os.environ.get("WOO_CONSUMER_KEY"),
                                    consumer_secret=os.environ.get("WOO_CONSUMER_SECRET"),
                                    version="wc/v3",
                                    timeout=20
                                )
                                # המרה למחרוזת
                                ids_str = ",".join(map(str, product_ids))
                                try:
                                    res = wcapi.get("products", params={"include": ids_str})
                                    if res.status_code == 200:
                                        for p in res.json():
                                            img_src = ""
                                            if p.get('images') and len(p['images']) > 0:
                                                img_src = p['images'][0]['src']
                                            
                                            # Clean HTML from short_description
                                            import re
                                            short_desc = p.get('short_description', '')
                                            if short_desc:
                                                # Remove HTML tags
                                                short_desc = re.sub(r'<[^>]+>', '', short_desc)
                                                # Remove extra whitespace
                                                short_desc = ' '.join(short_desc.split())

                                            # Get SKU
                                            sku = p.get('sku', '')

                                            products_data.append({
                                                "id": p.get('id'),
                                                "name": p.get('name'),
                                                "sku": sku,
                                                "price": f"{p.get('price')} ₪",
                                                "regular_price": f"{p.get('regular_price')} ₪",
                                                "sale_price": f"{p.get('sale_price')} ₪",
                                                "on_sale": p.get('on_sale', False),
                                                "image": img_src,
                                                "short_description": short_desc,
                                                "permalink": p.get('permalink'),
                                                "add_to_cart_url": f"{os.environ.get('WOO_BASE_URL')}/?add-to-cart={p.get('id')}"
                                            })
                                except Exception as woo_e:
                                    print(f"Woo Error: {woo_e}")

                            # ביטול הריצה ושליחת המידע לקליינט
                            client.beta.threads.runs.cancel(thread_id=thread_id, run_id=run.id)
                            
                            self.wfile.write(json.dumps({
                                "action": "show_products",
                                "products": products_data,
                                "reply": "מצאתי את המוצרים הבאים:",
                                "thread_id": thread_id
                            }).encode('utf-8'))
                            return

                elif run_status.status in ['failed', 'expired', 'cancelled']:
                    err = run_status.last_error.message if run_status.last_error else "Unknown AI Error"
                    self.wfile.write(json.dumps({"error": f"AI Error: {err}"}).encode('utf-8'))
                    break
                
                time.sleep(0.5)

        except Exception as e:
            # כאן הקסם: במקום לקרוס, אנחנו שולחים את השגיאה כ-JSON
            error_msg = f"SERVER ERROR: {str(e)}"
            trace = traceback.format_exc()
            print(trace) # ללוגים של ורסל
            self.wfile.write(json.dumps({
                "error": error_msg,
                "trace": trace
            }).encode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
