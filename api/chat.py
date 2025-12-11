from http.server import BaseHTTPRequestHandler
import json

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        try:
            # ייבוא דינמי
            try:
                from utils.ai import get_embedding, cosine_similarity, get_chat_response, classify_intent
                from utils.db import get_catalog
            except Exception as e:
                raise Exception(f"Import Error: {str(e)}")

            length = int(self.headers.get('content-length'))
            body = json.loads(self.rfile.read(length))
            
            user_message = body.get("message", "")
            history = body.get("history", [])
            
            # --- שלב 1: זיהוי כוונת הלקוח (AI) ---
            # ה-AI יחליט אם זה 'chat', 'search' או 'order'
            intent = classify_intent(user_message)
            print(f"Detected Intent: {intent}") # לוג לבדיקה

            context_str = "" # ברירת מחדל - אין קונטקסט
            response_items = [] # ברירת מחדל - אין כרטיסי מוצר

            # --- שלב 2: ביצוע פעולות לפי הכוונה ---
            
            # תרחיש א': הלקוח מחפש מוצר
            if intent == 'search':
                user_vector = get_embedding(user_message)
                catalog = get_catalog()
                
                if catalog:
                    scored_items = []
                    for item in catalog:
                        if 'embedding' in item:
                            score = cosine_similarity(user_vector, item['embedding'])
                            if score > 0.4: 
                                scored_items.append((score, item))
                    
                    scored_items.sort(key=lambda x: x[0], reverse=True)
                    
                    # אם נמצאו מוצרים רלוונטיים
                    if scored_items:
                        top_items = [item for score, item in scored_items[:5]]
                        response_items = top_items # נשלח לווידג'ט
                        
                        # נבנה טקסט ל-AI
                        for item in top_items:
                            raw = item.get('raw_text', str(item))
                            context_str += f"- {raw}\n"
            
            # תרחיש ב': הלקוח שואל על הזמנה (אופציונלי - כרגע רק הכוונה לבוט)
            elif intent == 'order':
                context_str = "SYSTEM NOTE: The user is asking about an order. Kindly ask for their phone number to verify their identity via SMS."

            # תרחיש ג' (chat): הלקוח מברך לשלום -> לא עושים כלום, משאירים context_str ריק.

            # --- שלב 3: תשובת הבוט הסופית ---
            ai_reply = get_chat_response(history + [{"role": "user", "content": user_message}], context_str)
            
            response_data = {
                "message": ai_reply,
                "items": response_items # יהיה מלא רק אם הכוונה הייתה 'search' ונמצאו מוצרים
            }

        except Exception as e:
            print(f"Error: {str(e)}")
            response_data = {"error": str(e)}

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(response_data).encode('utf-8'))
