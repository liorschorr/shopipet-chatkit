from http.server import BaseHTTPRequestHandler
import json
import os
import time
from openai import OpenAI
from woocommerce import API

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # כותרות תגובה
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        try:
            # 1. קריאת המידע מהדפדפן
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            
            user_msg = data.get('message')
            thread_id = data.get('thread_id')

            # 2. בדיקת הגדרות
            if not os.environ.get("OPENAI_API_KEY"):
                raise Exception("Missing OPENAI_API_KEY")
            
            # 3. אתחול OpenAI
            client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            assistant_id = os.environ.get("OPENAI_ASSISTANT_ID")

            # 4. ניהול שיחה (Thread)
            if not thread_id:
                thread = client.beta.threads.create()
                thread_id = thread.id
            
            # שליחת הודעה
            client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=user_msg
            )

            # הרצת ה-Assistant
            run = client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=assistant_id
            )

            # 5. המתנה לתשובה (Polling Loop)
            # לולאה פשוטה ללא סיבוכים
            while True:
                run_status = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
                
                if run_status.status == 'completed':
                    # יש תשובה טקסטואלית רגילה
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
                    # הבוט רוצה להפעיל כלי (כמו הצגת מוצרים)
                    tool_calls = run_status.required_action.submit_tool_outputs.tool_calls
                    
                    # משתנה לשמירת התשובה ללקוח
                    final_response = None

                    for tool in tool_calls:
                        func_name = tool.function.name
                        args = json.loads(tool.function.arguments)

                        # --- זיהוי הכלי: הצגת מוצרים ---
                        if func_name == "show_products":
                            # אתחול ווקומרס (רק אם צריך)
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
                                            # בניית אובייקט פשוט ל-Frontend
                                            products_data.append({
                                                "id": p['id'],
                                                "name": p['name'],
                                                "price": str(p['price']) + " ₪",
                                                "regular_price": str(p['regular_price']) + " ₪",
                                                "sale_price": str(p['sale_price']) + " ₪",
                                                "on_sale": p['on_sale'],
                                                "image": p['images'][0]['src'] if p['images'] else "",
                                                "permalink": p['permalink'],
                                                "add_to_cart_url": f"{os.environ.get('WOO_BASE_URL')}/?add-to-cart={p['id']}"
                                            })
                                except:
                                    pass # התעלמות משגיאות ווקומרס כדי לא להפיל את הצ'אט
