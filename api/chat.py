from http.server import BaseHTTPRequestHandler
import json
import os
import time
import requests
from openai import OpenAI

# הגדרות
# Ensure these are set in your environment
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
ASSISTANT_ID = os.environ.get("OPENAI_ASSISTANT_ID")

def check_woocommerce_order(phone):
    print(f"DEBUG: Checking order for phone {phone}") # Log tool usage
    url = os.environ.get("WOO_BASE_URL")
    key = os.environ.get("WOO_CONSUMER_KEY")
    secret = os.environ.get("WOO_CONSUMER_SECRET")
    
    try:
        res = requests.get(f"{url}/wp-json/wc/v3/orders", auth=(key, secret), params={"search": phone})
        res.raise_for_status() # Check for HTTP errors
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
        print(f"ERROR in check_woocommerce_order: {e}") # Log function errors
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
            thread_id = body.get("thread_id")

            print(f"DEBUG: Processing message: {user_msg} | Thread: {thread_id}")

            # 1. ניהול שיחה (Thread)
            if not thread_id:
                thread = client.beta.threads.create()
                thread_id = thread.id
                print(f"DEBUG: Created new thread {thread_id}")
            
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

            # 3. לולאת המתנה (Polling)
            bot_reply = ""
            start_time = time.time()
            
            while True:
                # BREAK LOOP if it takes too long (e.g., 50 seconds for Vercel limit)
                if time.time() - start_time > 50:
                    bot_reply = "Error: Timeout waiting for AI response."
                    print("DEBUG: Function timed out")
                    break

                run_status = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
                print(f"DEBUG: Run status: {run_status.status}") # CRITICAL LOG
                
                if run_status.status == 'completed':
                    msgs = client.beta.threads.messages.list(thread_id=thread_id)
                    # Get the latest message (first in list)
                    bot_reply = msgs.data[0].content[0].text.value
                    break
                
                elif run_status.status == 'requires_action':
                    print("DEBUG: Run requires action (tool call)")
                    tool_calls = run_status.required_action.submit_tool_outputs.tool_calls
                    tool_outputs = []
                    
                    for tool in tool_calls:
                        if tool.function.name == "get_order_status":
                            args = json.loads(tool.function.arguments)
                            phone = args.get("phone")
                            output = check_woocommerce_order(phone)
                            print(f"DEBUG: Tool output: {output}")
                            tool_outputs.append({"tool_call_id": tool.id, "output": output})
                    
                    if tool_outputs:
                        client.beta.threads.runs.submit_tool_outputs(
                            thread_id=thread_id,
                            run_id=run.id,
                            tool_outputs=tool_outputs
                        )
                    else:
                        print("DEBUG: No matching tool found for requires_action")

                elif run_status.status in ['failed', 'expired', 'cancelled']:
                    # Extract error details if available
                    error_msg = run_status.last_error.message if run_status.last_error else "Unknown error"
                    print(f"DEBUG: Run failed/expired. Error: {error_msg}")
                    bot_reply = "נתקלתי בבעיה טכנית בעיבוד הבקשה."
                    break
                
                time.sleep(1)

            # Clean response
            import re
            bot_reply = re.sub(r'【.*?】', '', bot_reply)
            
            print(f"DEBUG: Final Reply: {bot_reply}")

            response_data = {
                "message": bot_reply,
                "thread_id": thread_id 
            }

        except Exception as e:
            print(f"CRITICAL ERROR: {e}")
            response_data = {"error": str(e)}

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(response_data).encode('utf-8'))
