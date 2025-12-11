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
        try:
            length = int(self.headers.get('content-length'))
            body = json.loads(self.rfile.read(length))
            
            user_message = body.get("message")
            history = body.get("history", [])
            
            # --- שלב 1: חיבור ל-OpenAI ---
            try:
                user_vector = get_embedding(user_message)
            except Exception as e:
                raise Exception(f"OpenAI Error: {str(e)}")
            
            # --- שלב 2: שליפת קטלוג מ-Redis ---
            try:
                catalog = get_catalog()
            except Exception as e:
                raise Exception(f"Redis Error: {str(e)}")
            
            # אם הקטלוג ריק (לא הורץ עדכון, או שהעדכון נכשל)
            if not catalog:
                context_str = "Catalog is empty. Please run update_catalog."
            else:
                # --- שלב 3: חיפוש סמנטי ---
                scored_items = []
                for item in catalog:
                    if 'embedding' in item:
                        score = cosine_similarity(user_vector, item['embedding'])
                        if score > 0.4:
                            scored_items.append((score, item))
                
                scored_items.sort(key=lambda x: x[0], reverse=True)
                
                # בניית הקונטקסט
                context_str = ""
                for score, item in scored_items[:3]:
                    # שימוש בטקסט העשיר שיצרנו (raw_text) אם קיים, אחרת בונה מחדש
                    raw = item.get('raw_text', f"{item.get('name')} - {item.get('price')}")
                    context_str += f"- {raw}\n"
                    
                if not context_str:
                    context_str = "No specific products found matching this query."

            # --- שלב 4: תשובת AI סופית ---
            ai_reply = get_chat_response(history + [{"role": "user", "content": user_message}], context_str)
            
            response_data = {"reply": ai_reply}

        except Exception as e:
            # במקרה של שגיאה - נחזיר אותה לתוך הצ'אט כדי שנוכל לראות מה קרה
            response_data = {"reply": f"⚠️ שגיאת מערכת: {str(e)}"}

        # שליחת התשובה
        self.send_response(200)
        for k, v in cors_headers().items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(json.dumps(response_data).encode('utf-8'))
