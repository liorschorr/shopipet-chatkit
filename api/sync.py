from http.server import BaseHTTPRequestHandler
import json
import os
import traceback

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        response_data = {}
        current_version = "Unknown"

        try:
            # --- בדיקת גרסה (החלק החדש) ---
            try:
                import openai
                current_version = getattr(openai, "__version__", "Old/Unknown")
            except ImportError:
                current_version = "Not Installed"

            # טעינת ספריות
            from openai import OpenAI
            from woocommerce import API

            # --- בדיקת תאימות גרסה ---
            # אנחנו צריכים לפחות גרסה 1.35.0
            major, minor, _ = current_version.split('.')[:3]
            if int(major) < 1 or (int(major) == 1 and int(minor) < 35):
                 raise Exception(f"OpenAI Version is too old: {current_version}. We need >= 1.35.0. Please Redeploy without Cache.")

            # --- בדיקת משתנים ---
            if not os.environ.get("OPENAI_ASSISTANT_ID"):
                raise Exception("Missing Environment Variable: OPENAI_ASSISTANT_ID")
            
            # --- 1. משיכת מוצרים ---
            wcapi = API(
                url=os.environ.get("WOO_BASE_URL"),
                consumer_key=os.environ.get("WOO_CONSUMER_KEY"),
                consumer_secret=os.environ.get("WOO_CONSUMER_SECRET"),
                version="wc/v3",
                timeout=45
            )
            
            products_res = wcapi.get("products", params={"per_page": 50, "status": "publish"})
            products = products_res.json()
            
            # --- 2. יצירת קובץ ---
            content = ""
            if products:
                for p in products:
                    name = p.get('name', 'N/A')
                    price = p.get('price', '0')
                    link = p.get('permalink', '')
                    desc = str(p.get('short_description', '')).replace('<p>', '').replace('</p>', '').strip()
                    content += f"מוצר: {name}\nמחיר: {price}\nתיאור: {desc}\nקישור: {link}\n\n"
            else:
                content = "No products found."

            file_path = "/tmp/catalog.txt"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            # --- 3. OpenAI Upload ---
            client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            assistant_id = os.environ.get("OPENAI_ASSISTANT_ID")
            
            my_assistant = client.beta.assistants.retrieve(assistant_id)
            tool_res = my_assistant.tool_resources
            
            vs_id = None
            if tool_res and tool_res.file_search and tool_res.file_search.vector_store_ids:
                vs_id = tool_res.file_search.vector_store_ids[0]
            else:
                vs = client.beta.vector_stores.create(name="ShopiPet Store")
                vs_id = vs.id
                client.beta.assistants.update(
                    assistant_id=assistant_id,
                    tool_resources={"file_search": {"vector_store_ids": [vs_id]}}
                )

            with open(file_path, "rb") as f:
                client.beta.vector_stores.files.upload_and_poll(
                    vector_store_id=vs_id,
                    file=f
                )

            response_data = {
                "status": "success",
                "message": "Sync completed successfully",
                "installed_openai_version": current_version, # כאן נראה את הגרסה!
                "products_count": len(products) if products else 0
            }

        except Exception as e:
            print(f"ERROR: {traceback.format_exc()}")
            response_data = {
                "status": "error",
                "error": str(e),
                "installed_openai_version": current_version, # נראה גרסה גם בשגיאה
                "location": "Inside Handler Logic"
            }

        self.wfile.write(json.dumps(response_data).encode('utf-8'))
