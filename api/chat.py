from http.server import BaseHTTPRequestHandler
import json
import os
import time
import requests
from openai import OpenAI

# הגדרות
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
ASSISTANT_ID = os.environ.get("OPENAI_ASSISTANT_ID") # נצטרך להוסיף את זה ל-Vercel

# --- פונקציית העזר (הכלי שה-Agent משתמש בו) ---
def check_woocommerce_order(phone):
    url = os.environ.get("WOO_BASE_URL") # שים לב לשם המשתנה!
    key = os.environ.get("WOO_CONSUMER_KEY")
    secret = os.environ.get("WOO_CONSUMER_SECRET")
    
    try:
        # חיפוש הזמנה בווקומרס
        res = requests.get(f"{url}/wp-json/wc/v3/orders", auth=(key, secret), params={"search": phone})
        orders = res.json()
        
        if not orders:
            return json.dumps({"found": False, "msg": "לא מצאתי הזמנה לטלפון הזה."})
            
        order = orders[0]
        items_list = ", ".join([i['name'] for i in order['line_items']])
        return json.dumps({
            "found": True,
            "id": order['id'],
            "status": order['status'],
            "total": order['total'],
            "items": items_list
        })
    except Exception as e:
        return json.dumps({"error": str(e)})

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get('content-length'))
            body = json.loads(self.rfile.read(length))
            
            user_msg = body.get("message", "")
            # ה-Frontend ישלח לנו thread_id אם זו שיחה ממשיכה
            thread_id = body.get("thread_id")

            # 1. ניהול שיחה (Thread)
            if not thread_id:
                thread = client.beta.threads.create()
                thread_id = thread.id
            
            # הוספת הודעת המשתמש
            client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=user_msg
            )

            # 2. הרצת ה-Agent
            run = client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=ASSISTANT_ID
            )

            # 3. לולאת המתנה (Polling) - מחכים שה-Agent יחליט
            bot_reply = ""
            while True:
                run_status = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
                
                if run_status.status == 'completed':
                    # ה-Agent סיים לחשוב
                    msgs = client.beta.threads.messages.list(thread_id=thread_id)
                    bot_reply = msgs.data[0].content[0].text.value
                    break
                
                elif run_status.status == 'requires_action':
                    # ה-Agent מבקש להפעיל כלי (בדיקת הזמנה)
                    tool_calls = run_status.required_action.submit_tool_outputs.tool_calls
                    tool_outputs = []
                    
                    for tool in tool_calls:
                        if tool.function.name == "get_order_status":
                            args = json.loads(tool.function.arguments)
                            phone = args.get("phone")
                            # הפעלת הפונקציה שלנו בפייתון
                            output = check_woocommerce_order(phone)
                            tool_outputs.append({"tool_call_id": tool.id, "output": output})
                    
                    # החזרת התשובה ל-Agent
                    client.beta.threads.runs.submit_tool_outputs(
                        thread_id=thread_id,
                        run_id=run.id,
                        tool_outputs=tool_outputs
                    )
                
                elif run_status.status in ['failed', 'expired']:
                    bot_reply = "נתקלתי בבעיה טכנית. נסה שוב."
                    break
                
                time.sleep(1) # ממתינים שנייה

            # ניקוי הערות שוליים של OpenAI [source]
            import re
            bot_reply = re.sub(r'【.*?】', '', bot_reply)

            # החזרת תשובה + Thread ID (כדי שהדפדפן יזכור את השיחה)
            response_data = {
                "message": bot_reply,
                "thread_id": thread_id 
            }

        except Exception as e:
            print(f"Error: {e}")
            response_data = {"error": str(e)}

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(response_data).encode('utf-8'))
