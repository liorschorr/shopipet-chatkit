from http.server import BaseHTTPRequestHandler
import json
import os
import time
import requests
from openai import OpenAI
import traceback

# --- הגדרות ---
# שימוש ב-Init מוגן כדי למנוע קריסה בהתחלה
try:
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    ASSISTANT_ID = os.environ.get("OPENAI_ASSISTANT_ID")
except:
    client = None
    ASSISTANT_ID = None

# --- פונקציית העזר לבדיקת הזמנה ---
def check_woocommerce_order(phone):
    url = os.environ.get("WOO_BASE_URL")
    key = os.environ.get("WOO_CONSUMER_KEY")
    secret = os.environ.get("WOO_CONSUMER_SECRET")
    
    if not url or not key:
        return json.dumps({"error": "WooCommerce config missing"})

    try:
        # חיפוש הזמנה
        res = requests.get(f"{url}/wp-json/wc/v3/orders", auth=(key, secret), params={"search": phone}, timeout=10)
        
        if res.status_code != 200:
             return json.dumps({"error": f"WooCommerce Error: {res.status_code}"})

        orders = res.json()
        if not orders:
            return json.dumps({"found": False, "msg": "לא מצאתי הזמנה לטלפון הזה."})
            
        order = orders[0]
        # איסוף פריטים בצורה בטוחה
        items_names = [i.get('name', 'מוצר') for i in order.get('line_items', [])]
        items_list = ", ".join(items_names)
        
        return json.dumps({
            "found": True,
            "id": order.get('id'),
            "status": order.get('status'),
            "total": order.get('total'),
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
        # 1. שליחת כותרות מיד (מונע timeout של הדפדפן)
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        response_data = {}

        try:
            # בדיקת אתחול
            if not client:
                raise Exception("OpenAI Client failed to initialize. Check API Keys.")

            length = int(self.headers.get('content-length', 0))
            body = json.loads(self.rfile.read(length))
            
            user_msg = body.get("message", "")
            thread_id = body.get("thread_id")

            # 2. ניהול שיחה
            if not thread_id:
                thread = client.beta.threads.create()
                thread_id = thread.id
            
            client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=user_msg
            )

            # 3. הרצה
            run = client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=ASSISTANT_ID
            )

            # 4. לולאת המתנה עם שעון עצר (החלק החשוב!)
            bot_reply = "..."
            start_time = time.time()
            
            while True:
                # --- בדיקת הזמן ---
                # אם עברו 50 שניות, אנחנו חותכים כדי ש-Vercel לא יהרוג אותנו
                if time.time() - start_time > 50:
                    bot_reply = "⏱️ הבוט מתעכב בתשובה (Timeout). נסה לשאול שוב."
                    break

                run_status = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
                
                if run_status.status == 'completed':
                    msgs = client.beta.threads.messages.list(thread_id=thread_id)
                    # לוקחים את ההודעה האחרונה ומוודאים שהיא של ה-Assistant
                    latest_msg = msgs.data[0]
                    if latest_msg.role == 'assistant':
                        bot_reply = latest_msg.content[0].text.value
                    else:
                        bot_reply = "לא התקבלה תשובה ברורה (No Reply)."
                    break
                
                elif run_status.status == 'requires_action':
                    tool_calls = run_status.required_action.submit_tool_outputs.tool_calls
                    tool_outputs = []
                    
                    for tool in tool_calls:
                        func_name = tool.function.name
                        args = json.loads(tool.function.arguments)

                        # טיפול בבדיקת הזמנה
                        if func_name == "get_order_status":
                            phone = args.get("phone")
                            output = check_woocommerce_order(phone)
                            tool_outputs.append({"tool_call_id": tool.id, "output": output})
                        
                        # טיפול בהצגת מוצרים (אם תרצה להחזיר את זה)
                        elif func_name == "show_products":
                            # כרגע נחזיר תשובה ריקה כדי לא לשבור, 
                            # או שתעתיק לפה את הקוד מהשלבים הקודמים
                            tool_outputs.append({"tool_call_id": tool.id, "output": "OK"})

                    if tool_outputs:
                        client.beta.threads.runs.submit_tool_outputs(
                            thread_id=thread_id,
                            run_id=run.id,
                            tool_outputs=tool_outputs
                        )
                
                elif run_status.status in ['failed', 'expired', 'cancelled']:
                    error_detail = run_status.last_error.message if run_status.last_error else "Unknown"
                    bot_reply = f"שגיאה בעיבוד הבקשה ב-OpenAI: {error_detail}"
                    break
                
                time.sleep(1) # המתנה של שנייה בין בדיקות

            # ניקוי הערות שוליים
            import re
            bot_reply = re.sub(r'【.*?】', '', str(bot_reply))

            response_data = {
                "reply": bot_reply, # שים לב: ב-Frontend שלך הקוד מצפה ל-reply או message? בדוק ב-js
                "message": bot_reply, # שולח בשני השמות ליתר ביטחון
                "thread_id": thread_id 
            }

        except Exception as e:
            # תפיסת שגיאות קריטית
            print(f"CRITICAL ERROR: {traceback.format_exc()}")
            response_data = {"error": str(e), "message": f"שגיאת שרת: {str(e)}"}

        # כתיבת התשובה הסופית
        self.wfile.write(json.dumps(response_data).encode('utf-8'))
