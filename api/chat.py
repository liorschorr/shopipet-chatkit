from http.server import BaseHTTPRequestHandler
import json
import os
import time
from openai import OpenAI
from woocommerce import API

# אתחול
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
ASSISTANT_ID = os.environ.get("OPENAI_ASSISTANT_ID")

# חיבור לווקומרס (לשליפת תמונות ומחירים בזמן אמת)
wcapi = API(
    url=os.environ.get("WOO_BASE_URL"),
    consumer_key=os.environ.get("WOO_CONSUMER_KEY"),
    consumer_secret=os.environ.get("WOO_CONSUMER_SECRET"),
    version="wc/v3",
    timeout=30
)

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data)
        
        user_msg = data.get('message')
        thread_id = data.get('thread_id')

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        try:
            # 1. ניהול ה-Thread
            if not thread_id:
                thread = client.beta.threads.create()
                thread_id = thread.id
            
            # 2. הוספת הודעת משתמש
            client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=user_msg
            )

            # 3. הרצת ה-Assistant
            run = client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=ASSISTANT_ID
            )

            # 4. Polling (המתנה לתשובה)
            while True:
                run_status = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
                
                if run_status.status == 'completed':
                    # שליפת התשובה הטקסטואלית
                    messages = client.beta.threads.messages.list(thread_id=thread_id)
                    reply = messages.data[0].content[0].text.value
                    
                    # ניקוי הערות שוליים מעצבנות של OpenAI
                    import re
                    reply = re.sub(r'【.*?†source】', '', reply)
                    
                    self.wfile.write(json.dumps({
                        "reply": reply, 
                        "thread_id": thread_id
                    }).encode('utf-8'))
                    break
                
                elif run_status.status == 'requires_action':
                    # הבוט רוצה להפעיל פונקציה (כלי)
                    tool_calls = run_status.required_action.submit_tool_outputs.tool_calls
                    
                    tool_outputs = []
                    response_payload = {"thread_id": thread_id}

                    for tool in tool_calls:
                        func_name = tool.function.name
                        args = json.loads(tool.function.arguments)

                        # --- מקרה 1: הצגת מוצרים (UI) ---
                        if func_name == "show_products":
                            product_ids = args.get("product_ids", [])
                            
                            # משיכת פרטים מלאים מווקומרס עבור ה-IDs האלו
                            products_data = []
                            if product_ids:
                                ids_str = ",".join(map(str, product_ids))
                                woo_res = wcapi.get("products", params={"include": ids_str})
                                if woo_res.status_code == 200:
                                    raw_products = woo_res.json()
                                    for p in raw_products:
                                        products_data.append({
                                            "id": p['id'],
                                            "name": p['name'],
                                            "price": p['price'],
                                            "regular_price": p['regular_price'],
                                            "sale_price": p['sale_price'],
                                            "on_sale": p['on_sale'],
                                            "image": p['images'][0]['src'] if p['images'] else "https://via.placeholder.com/150",
                                            "permalink": p['permalink'],
                                            "add_to_cart_url": f"{os.environ.get('WOO_BASE_URL')}/?add-to-cart={p['id']}"
                                        })

                            # אנו שולחים את המידע לקליינט מיד, ומבטלים את הריצה כדי שהבוט לא יקשקש טקסט מיותר
                            client.beta.threads.runs.cancel(thread_id=thread_id, run_id=run.id)
                            
                            response_payload["reply"] = "הנה המוצרים שמצאתי עבורך:" # כותרת לפני הכרטיסיות
                            response_payload["action"] = "show_products"
                            response_payload["products"] = products_data
                            
                            self.wfile.write(json.dumps(response_payload).encode('utf-8'))
                            return # מסיימים כאן

                        # --- מקרה 2: בדיקת הזמנה ---
                        elif func_name == "check_order":
                            phone = args.get("phone_number")
                            # כאן תהיה הלוגיקה של בדיקת הזמנה (נשאיר placeholder בינתיים)
                            tool_outputs.append({
                                "tool_call_id": tool.id,
                                "output": json.dumps({"status": "not_found", "message": "Demo Mode"})
                            })

                    # אם זה לא show_products, ממשיכים את הריצה הרגילה
                    if tool_outputs:
                        client.beta.threads.runs.submit_tool_outputs(
                            thread_id=thread_id,
                            run_id=run.id,
                            tool_outputs=tool_outputs
                        )

                elif run_status.status in ['failed', 'cancelled', 'expired']:
                    self.wfile.write(json.dumps({"error": "Run failed"}).encode('utf-8'))
                    break
                
                time.sleep(0.5)

        except Exception as e:
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
