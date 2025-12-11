from http.server import BaseHTTPRequestHandler
import json
import os
import random
import redis
import requests
from utils.cors import cors_headers

# חיבור ל-Redis
r = redis.from_url(os.environ.get("KV_URL"))

def normalize_phone_il(phone):
    """
    מנרמל מספר ישראלי לפורמט בינלאומי ללא פלוס.
    050-1234567 -> 972501234567
    """
    # הסרת מקפים ורווחים
    clean = ''.join(filter(str.isdigit, phone))
    
    # אם מתחיל ב-0, מורידים אותו ומוסיפים 972
    if clean.startswith('0'):
        clean = '972' + clean[1:]
    # אם כבר מתחיל ב-972, משאירים
    
    return clean

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        for k, v in cors_headers().items():
            self.send_header(k, v)
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get('content-length'))
            body = json.loads(self.rfile.read(length))
            phone_input = body.get("phone")

            if not phone_input:
                self.send_error(400, "Phone required")
                return

            # 1. נרמול המספר לפורמט של Flashy
            phone_formatted = normalize_phone_il(phone_input)

            # 2. יצירת קוד בן 5 ספרות
            otp_code = str(random.randint(10000, 99999))

            # 3. שמירה ב-Redis ל-5 דקות
            # שים לב: המפתח נשמר לפי המספר שהמשתמש הזין (כדי שיהיה קל לאמת אח"כ)
            r.setex(f"otp:{phone_input}", 300, otp_code)

            # 4. שליחה דרך Flashy API
            flashy_key = os.environ.get("FLASHY_API_KEY")
            sender_id = os.environ.get("FLASHY_SENDER_ID")
            
            # כתובת ה-API של Flashy לשליחת SMS
            url = "https://flashyapp.com/api/2.0/sms/send"
            
            payload = {
                "token": flashy_key,
                "from": sender_id,
                "to": phone_formatted,
                "message": f"קוד האימות שלך ל-ShopiPet הוא: {otp_code}"
            }
            
            # ביצוע השליחה
            res = requests.post(url, json=payload)
            
            # בדיקה אם Flashy החזיר שגיאה
            if res.status_code != 200:
                raise Exception(f"Flashy Error: {res.text}")

            # תשובה ללקוח
            self.send_response(200)
            for k, v in cors_headers().items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(json.dumps({"status": "sent", "message": "SMS sent successfully"}).encode('utf-8'))

        except Exception as e:
            self.send_response(500)
            for k, v in cors_headers().items():
                self.send_header(k, v)
            self.end_headers()
            print(f"Error sending SMS: {str(e)}") # יופיע בלוגים של Vercel
            self.wfile.write(json.dumps({"error": "Failed to send SMS"}).encode('utf-8'))
