from http.server import BaseHTTPRequestHandler
import json
from utils.cors import cors_headers

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        for k, v in cors_headers().items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok", "service": "ShopiPet ChatKit"}).encode('utf-8'))
