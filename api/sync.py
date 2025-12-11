from http.server import BaseHTTPRequestHandler
import json
import os
import traceback # ספרייה שעוזרת להציג את השגיאה המלאה

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # כותרות בסיסיות כדי שהדפדפן תמיד יציג את התשובה
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        response_data = {}

        try:
            # --- שלב 1: בדיקת ספריות (Imports) ---
            try:
                from openai import OpenAI
                from woocommerce import API
            except ImportError as e:
                raise Exception(f"Library missing: {str(e)}. Did you install requirements.txt?")

            # --- שלב 2: בדיקת משתני סביבה ---
            required_vars = [
                "OPENAI_API_KEY", 
                "OPENAI_ASSISTANT_ID", 
                "WOO_BASE_URL", 
                "WOO_CONSUMER_KEY", 
                "WOO_CONSUMER_SECRET"
            ]
            
            missing = [var for var in required_vars if not os.environ.get(var)]
            if missing:
                raise Exception(f"Missing Environment Variables: {', '.join(missing)}")

            # --- שלב 3: התחברות ל-WooCommerce ---
            wcapi = API(
                url=os.environ.get("WOO_BASE_URL"),
                consumer_key=os.environ.get("WOO_CONSUMER_KEY"),
                consumer_secret=os.environ.get("WOO_CONSUMER_SECRET"),
                version="wc/v3",
                timeout=30
            )
            
            # בדיקת תקשורת מינימלית
            products = wcapi.get("products", params={"per_page": 50, "status": "publish"}).json()
            
            # בדיקה אם התגובה היא בכלל רשימה (ולא שגיאה של ווקומרס)
            if isinstance(products, dict) and "message" in products:
                raise Exception(f"WooCommerce Error: {products['message']}")
                
            if not products:
                response_data = {"status": "warning", "msg": "Connected to Woo, but found 0 products."}
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
                return

            # --- שלב 4: הכנת הקובץ ---
            content = ""
            for p in products:
                # הגנה מפני שדות חסרים
                name = p.get('name', 'Unknown')
                price = p.get('price', '0')
                link = p.get('permalink', '')
                content += f"מוצר: {name}\nמחיר: {price}\nקישור: {link}\n\n"
            
            # שמירה לתיקיית TMP (המקום היחיד שמותר לכתוב בו ב-Vercel)
            file_path = "/tmp/catalog.txt"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            # --- שלב 5: שליחה ל-OpenAI ---
            client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            assistant_id = os.environ.get("OPENAI_ASSISTANT_ID")
            
            # שליפת ה-Assistant כדי לקבל את ה-Vector Store
            my_assistant = client.beta.assistants.retrieve(assistant_id)
            tool_res = my_assistant.tool_resources
            
            vs_id = None
            if tool_res and tool_res.file_search and tool_res.file_search.vector_store_ids:
                vs_id = tool_res.file_search.vector_store_ids[0]
            else:
                # יצירה אם אין
                vs = client.beta.vector_stores.create(name="ShopiPet Store")
                vs_id = vs.id
                client.beta.assistants.update(
                    assistant_id=assistant_id,
                    tool_resources={"file_search": {"vector_store_ids": [vs_id]}}
                )

            # העלאה
            with open(file_path, "rb") as f:
                client.beta.vector_stores.files.upload_and_poll(
                    vector_store_id=vs_id,
                    file=f
                )

            # --- סיום מוצלח ---
            response_data = {
                "status": "success", 
                "message": "Process Completed Successfully",
                "products_found": len(products),
                "openai_vector_store": vs_id
            }

        except Exception as e:
            # --- תפיסת כל שגיאה אפשרית ---
            # כאן אנחנו תופסים את הקריסה ומדפיסים אותה למסך במקום לקבל 500
            error_details = traceback.format_exc()
            print(f"CRITICAL ERROR: {error_details}") # ללוגים
            response_data = {
                "status": "error",
                "error_message": str(e),
                "traceback": error_details # הדפסה מלאה של איפה הקוד נפל
            }

        # כתיבת התשובה הסופית (JSON) לדפדפן
        self.wfile.write(json.dumps(response_data).encode('utf-8'))
