from http.server import BaseHTTPRequestHandler
import json
import os
import time
import re
from openai import OpenAI
from woocommerce import API

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        try:
            # 1. קריאת המידע מהבקשה
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            
            user_msg = data.get('message')
            thread_id = data.get('thread_id')

            if not user_msg:
                raise Exception("Missing 'message' in request body")

            # 2. בדיקת משתני סביבה
            required_vars = ["OPENAI_API_KEY", "OPENAI_ASSISTANT_ID"]
            missing = [var for var in required_vars if not os.environ.get(var)]
            if missing:
                raise Exception(f"Missing Environment Variables: {', '.join(missing)}")

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
            max_attempts = 60  # מקסימום 60 שניות
            attempt = 0
            
            while attempt < max_attempts:
                run_status = client.beta.threads.runs.retrieve(
                    thread_id=thread_id, 
                    run_id=run.id
                )
                
                # --- סטטוס: הושלם ---
                if run_status.status == 'completed':
                    messages = client.beta.threads.messages.list(thread_id=thread_id)
                    reply = messages.data[0].content[0].text.value
                    
                    # ניקוי הערות שוליים
                    reply = re.sub(r'【.*?†source】', '', reply)
                    
                    self.wfile.write(json.dumps({
                        "status": "success",
                        "reply": reply, 
                        "thread_id": thread_id
                    }, ensure_ascii=False).encode('utf-8'))
                    return
                
                # --- סטטוס: נכשל ---
                elif run_status.status in ['failed', 'cancelled', 'expired']:
                    error_msg = getattr(run_status, 'last_error', None)
                    raise Exception(f"Run {run_status.status}: {error_msg}")
                
                # --- סטטוס: דורש פעולה (Function Calling) ---
                elif run_status.status == 'requires_action':
                    tool_calls = run_status.required_action.submit_tool_outputs.tool_calls
                    tool_outputs = []
                    products_for_frontend = []

                    for tool in tool_calls:
                        func_name = tool.function.name
                        args = json.loads(tool.function.arguments)
                        output = ""

                        # --- כלי: הצגת מוצרים ---
                        if func_name == "show_products":
                            product_ids = args.get("product_ids", [])
                            
                            if product_ids:
                                try:
                                    wcapi = API(
                                        url=os.environ.get("WOO_BASE_URL"),
                                        consumer_key=os.environ.get("WOO_CONSUMER_KEY"),
                                        consumer_secret=os.environ.get("WOO_CONSUMER_SECRET"),
                                        version="wc/v3",
                                        timeout=20
                                    )
                                    
                                    ids_str = ",".join(map(str, product_ids))
                                    woo_res = wcapi.get("products", params={"include": ids_str})
                                    
                                    if woo_res.status_code == 200:
                                        raw_products = woo_res.json()
                                        for p in raw_products:
                                            products_for_frontend.append({
                                                "id": p['id'],
                                                "name": p['name'],
                                                "price": f"{p['price']} ₪",
                                                "regular_price": f"{p.get('regular_price', '')} ₪" if p.get('regular_price') else "",
                                                "sale_price": f"{p.get('sale_price', '')} ₪" if p.get('sale_price') else "",
                                                "on_sale": p.get('on_sale', False),
                                                "image": p['images'][0]['src'] if p.get('images') else "",
                                                "permalink": p['permalink'],
                                                "ad
