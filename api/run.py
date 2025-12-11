from http.server import BaseHTTPRequestHandler
import json
import os
import traceback

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        try:
            # בדיקת ספריות
            from openai import OpenAI
            from woocommerce import API
            
            # בדיקת משתנים
            if not os.environ.get("OPENAI_ASSISTANT_ID"):
                raise Exception("Missing OPENAI_ASSISTANT_ID")

            # משיכת מוצרים
            wcapi = API(
                url=os.environ.get("WOO_BASE_URL"),
                consumer_key=os.environ.get("WOO_CONSUMER_KEY"),
                consumer_secret=os.environ.get("WOO_CONSUMER_SECRET"),
                version="wc/v3",
                timeout=30
            )
            
            products = wcapi.get("products", params={"per_page": 50, "status": "publish"}).json()
            
            if not products:
                self.wfile.write(json.dumps({"status": "warning", "msg": "No products found"}).encode('utf-8'))
                return

            # יצירת קובץ
            content = ""
            for p in products:
                content += f"מוצר: {p['name']}\nמחיר: {p.get('price','0')}\nקישור: {p.get('permalink','')}\n\n"
            
            file_path = "/tmp/catalog.txt"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            # שליחה ל-OpenAI
            client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            assistant_id = os.environ.get("OPENAI_ASSISTANT_ID")
            
            # בדיקת Vector Store
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

            self.wfile.write(json.dumps({
                "status": "success", 
                "products": len(products),
                "filename": "run.py",
                "version": "DIRECT GITHUB UPLOAD"
            }).encode('utf-8'))

        except Exception as e:
            self.wfile.write(json.dumps({
                "status": "error",
                "error": str(e),
                "trace": traceback.format_exc()
            }).encode('utf-8'))
