from http.server import BaseHTTPRequestHandler
import json
import os
from openai import OpenAI
from woocommerce import API

# אתחול
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
ASSISTANT_ID = os.environ.get("OPENAI_ASSISTANT_ID")

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # בדיקה מקדימה
            if not ASSISTANT_ID:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Missing OPENAI_ASSISTANT_ID"}).encode('utf-8'))
                return

            # 1. משיכת מוצרים
            wcapi = API(
                url=os.environ.get("WOO_BASE_URL"),
                consumer_key=os.environ.get("WOO_CONSUMER_KEY"),
                consumer_secret=os.environ.get("WOO_CONSUMER_SECRET"),
                version="wc/v3",
                timeout=60
            )
            
            # מושך 200 מוצרים
            products = wcapi.get("products", params={"per_page": 200, "status": "publish"}).json()
            
            if not products:
                self.send_response(200)
                self.wfile.write(json.dumps({"status": "error", "msg": "No products found"}).encode('utf-8'))
                return

            # 2. יצירת תוכן
            content = ""
            for p in products:
                price = p['sale_price'] if p['on_sale'] else p['regular_price']
                stock = "במלאי" if p['stock_status'] == 'instock' else "חסר"
                desc = str(p['short_description']).replace('<p>','').replace('</p>','')
                
                content += f"מוצר: {p['name']}\nמחיר: {price} שח\nמלאי: {stock}\nתיאור: {desc}\nקישור: {p['permalink']}\nתמונה: {p['images'][0]['src'] if p['images'] else ''}\n\n"
            
            # שמירה זמנית
            file_path = "/tmp/catalog.txt"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            # 3. העלאה ל-OpenAI Agent
            my_assistant = client.beta.assistants.retrieve(ASSISTANT_ID)
            tool_res = my_assistant.tool_resources
            vs_id = None
            
            if tool_res and tool_res.file_search and tool_res.file_search.vector_store_ids:
                vs_id = tool_res.file_search.vector_store_ids[0]
            else:
                vs = client.beta.vector_stores.create(name="ShopiPet Store")
                vs_id = vs.id
                client.beta.assistants.update(
                    assistant_id=ASSISTANT_ID,
                    tool_resources={"file_search": {"vector_store_ids": [vs_id]}}
                )

            with open(file_path, "rb") as f:
                client.beta.vector_stores.files.upload_and_poll(
                    vector_store_id=vs_id,
                    file=f
                )

            self.send_response(200)
            self.end_headers()
            
            response_data = {
                "status": "success",
                "items_count": len(products),
                "version": "1.0 - LATEST CODE (OpenAI Agent - Underscore Version)" 
            }
            self.wfile.write(json.dumps(response_data).encode('utf-8'))

        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
