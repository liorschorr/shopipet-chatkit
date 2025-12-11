from http.server import BaseHTTPRequestHandler
import json
import os
import redis
import requests
from utils.cors import cors_headers

r = redis.from_url(os.environ.get("KV_URL"))

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        for k, v in cors_headers().items():
            self.send_header(k, v)
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get('content-length'))
        body = json.loads(self.rfile.read(length))
        
        phone = body.get("phone")
        user_code = body.get("code")

        # אימות מול Redis
        stored_code = r.get(f"otp:{phone}")
        
        if not stored_code or stored_code.decode('utf-8') != user_code:
            self.send_response(401)
            for k, v in cors_headers().items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(json.dumps({"success": False, "message": "Code Invalid"}).encode('utf-8'))
            return

        # מחיקת הקוד לאחר שימוש
        r.delete(f"otp:{phone}")

        # שליפת הזמנות מווקומרס
        wc_url = os.environ.get("WC_URL")
        auth = (os.environ.get("WC_CONSUMER_KEY"), os.environ.get("WC_CONSUMER_SECRET"))
        
        try:
            res = requests.get(f"{wc_url}/wp-json/wc/v3/orders", auth=auth, params={"search": phone}, timeout=10)
            orders = res.json()
            
            formatted_orders = []
            if orders:
                for order in orders[:3]:
                    formatted_orders.append({
                        "id": order['id'],
                        "status": order['status'],
                        "total": f"{order['total']} {order['currency_symbol']}",
                        "date": order['date_created'],
                        "items": [item['name'] for item in order['line_items']]
                    })
            
            data = {"success": True, "orders": formatted_orders}

        except Exception as e:
            data = {"success": False, "error": str(e)}

        self.send_response(200)
        for k, v in cors_headers().items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
