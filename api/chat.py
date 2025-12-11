from http.server import BaseHTTPRequestHandler
import json
import numpy as np
from utils.cors import cors_headers
from utils.db import get_catalog
from utils.ai import get_embedding, cosine_similarity, get_chat_response

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        for k, v in cors_headers().items():
            self.send_header(k, v)
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get('content-length'))
        body = json.loads(self.rfile.read(length))
        
        user_message = body.get("message")
        history = body.get("history", [])
        
        # 1. יצירת וקטור לשאלה
        user_vector = get_embedding(user_message)
        
        # 2. שליפת קטלוג וחיפוש
        catalog = get_catalog()
        scored_items = []
        for item in catalog:
            if 'embedding' in item:
                score = cosine_similarity(user_vector, item['embedding'])
                if score > 0.4:
                    scored_items.append((score, item))
        
        scored_items.sort(key=lambda x: x[0], reverse=True)
        
        # 3. בניית קונטקסט
        context_str = ""
        for score, item in scored_items[:3]:
            context_str += f"- {item['raw_text']}\n" # שימוש בטקסט העשיר שיצרנו
            
        if not context_str:
            context_str = "No specific products found."

        # 4. תשובת AI
        ai_reply = get_chat_response(history + [{"role": "user", "content": user_message}], context_str)
        
        self.send_response(200)
        for k, v in cors_headers().items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(json.dumps({"reply": ai_reply}).encode('utf-8'))
