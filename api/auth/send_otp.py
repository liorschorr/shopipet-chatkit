from http.server import BaseHTTPRequestHandler
import json
import os
import random
import redis
import requests
from utils.cors import cors_headers

# שינוי: שימוש ב-REDIS URL שלך
redis_url = os.environ.get("shopipetbot_REDIS_URL")
r = redis.from_url(redis_url, ssl_cert_reqs=None)

def normalize_phone_il(phone):
    clean = ''.join(filter(str.isdigit, phone))
    if clean.startswith('0'):
        clean = '972' + clean[1:]
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

            phone_formatted = normalize_phone_il(phone_input)
            otp_code = str(random.randint(10000, 99999))
            
            r.setex(f"otp:{phone_input}", 300, otp_code)

            url = "https://flashyapp.com/api/2.0/sms/send"
            payload = {
                "token": os.environ.get("FLASHY_API_KEY"),
                "from": os.environ.get("FLASHY_SENDER_ID"),
                "to": phone_formatted,
                "message": f"ShopiPet Code: {otp_code}"
            }
            
            res = requests.post(url, json=payload)
            if res.status_code != 200:
                print(f"Flashy Error: {res.text}")
                raise Exception("SMS Provider Error")

            self.send_response(200)
            for k, v in cors_headers().items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(json.dumps({"status": "sent"}).encode('utf-8'))

        except Exception as e:
            self.send_response(500)
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
