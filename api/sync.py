from http.server import BaseHTTPRequestHandler
import json
import os
import traceback

# Vercel מחפש את המחלקה הזו בדיוק בשם הזה
class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # 1. שליחת כותרות תקינות מיד (כדי למנוע timeout/404)
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        response_data = {}

        try:
            # --- טעינת ספריות בתוך הפונקציה (Lazy Loading) ---
            # זה מונע קריסה של ה-Handler אם יש בעיה בהתקנות
            try:
                from openai import OpenAI
                from woocommerce import API
            except ImportError as e:
                raise Exception(f"CRITICAL: Failed to import libraries. Check requirements.txt. Details: {e}")

            # --- בדיקת משתנים ---
            if not os.environ.get("OPENAI_ASSISTANT_ID"):
                raise Exception("Missing Environment Variable: OPENAI_ASSISTANT_ID")
            
            if not os.environ.get("OPENAI_API_KEY"):
                raise Exception("Missing Environment Variable: OPENAI_API_KEY")

            # --- 1. משיכת מוצרים מ-WooCommerce ---
            wcapi = API(
                url=os.environ.get("WOO_BASE_URL"),
                consumer_key=os.environ.get("WOO_CONSUMER_KEY"),
                consumer_secret=os.environ.get("WOO_CONSUMER_SECRET"),
                version="wc/v3",
                timeout=45
            )
            
            # ניסיון משיכה
            products_res = wcapi.get("products", params={"per_page": 50, "status": "publish"})
            
            if products_res.status_code != 200:
                 raise Exception(f"WooCommerce Error {products_res.status_code}: {products_res.text}")
                 
            products = products_res.json()
            
            # --- 2. יצירת קובץ ---
            content = ""
            if products:
                for p in products:
                    name = p.get('name', 'N/A')
                    price = p.get('price', '0')
                    link = p.get('permalink', '')
                    # ניקוי תגיות HTML פשוט
                    desc = str(p.get('short_description', '')).replace('<p>', '').replace('</p>', '').strip()
                    content += f"מוצר: {name}\nמחיר: {price}\nתיאור: {desc}\nקישור: {link}\n\n"
            else:
                content = "No products found in store."

            file_path = "/tmp/catalog.txt"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            # --- 3. OpenAI Upload ---
            client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            assistant_id = os.environ.get("OPENAI_ASSISTANT_ID")
            
            my_assistant = client.beta.assistants.retrieve(assistant_id)
            tool_res = my_assistant.tool_resources
            
            vs_id = None
            # בדיקה אם קיים Vector Store
            if tool_res and tool_res.file_search and tool_res.file_search.vector_store_ids:
                vs_id = tool_res.file_search.vector_store_ids[0]
            else:
                # יצירה חדשה
                vs = client.beta.vector_stores.create(name="ShopiPet Store")
                vs_id = vs.id
                client.beta.assistants.update(
                    assistant_id=assistant_id,
                    tool_resources={"file_search": {"vector_store_ids": [vs_id]}}
                )

            # העלאת הקובץ
            with open(file_path, "rb") as f:
                client.beta.vector_stores.files.upload_and_poll(
                    vector_store_id=vs_id,
                    file=f
                )

            response_data = {
                "status": "success",
                "message": "Sync completed successfully",
                "products_count": len(products) if products else 0,
                "vector_store_id": vs_id
            }

        except Exception as e:
            # במקרה של שגיאה - מחזירים אותה כ-JSON במקום לקרוס
            print(f"ERROR: {traceback.format_exc()}")
            response_data = {
                "status": "error",
                "error": str(e),
                "location": "Inside Handler Logic"
            }

        # כתיבת התשובה הסופית
        self.wfile.write(json.dumps(response_data).encode('utf-8'))
