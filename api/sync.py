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

        try:
            # --- טעינת ספריות ---
            try:
                from openai import OpenAI
                from woocommerce import API
            except ImportError as e:
                raise Exception(f"CRITICAL: Libraries missing. Check requirements.txt. Details: {e}")

            # --- בדיקת משתנים ---
            required_vars = ["OPENAI_API_KEY", "OPENAI_ASSISTANT_ID", "WOO_BASE_URL", "WOO_CONSUMER_KEY", "WOO_CONSUMER_SECRET"]
            missing = [var for var in required_vars if not os.environ.get(var)]
            if missing:
                raise Exception(f"Missing Env Vars: {', '.join(missing)}")

            # --- 1. משיכת מוצרים מ-WooCommerce ---
            wcapi = API(
                url=os.environ.get("WOO_BASE_URL"),
                consumer_key=os.environ.get("WOO_CONSUMER_KEY"),
                consumer_secret=os.environ.get("WOO_CONSUMER_SECRET"),
                version="wc/v3",
                timeout=60
            )
            
            # משיכת 100 מוצרים (או יותר בלולאה אם צריך)
            products_res = wcapi.get("products", params={"per_page": 100, "status": "publish"})
            
            if products_res.status_code != 200:
                 raise Exception(f"WooCommerce Error {products_res.status_code}: {products_res.text}")
                 
            products = products_res.json()
            
            # --- 2. עיבוד הנתונים לקובץ טקסט ---
            content = ""
            if products:
                for p in products:
                    system_id = p.get('id')
                    name = p.get('name', 'N/A')
                    link = p.get('permalink', '')
                    
                    # --- לוגיקה לזיהוי מק"ט (כולל ברקודים) ---
                    display_sku = p.get('sku')
                    if not display_sku:
                        # חיפוש בשדות Meta נפוצים לברקודים
                        for meta in p.get('meta_data', []):
                            if meta.get('key') in ['_gtin', 'gtin', 'gtin_code', '_ean', 'ean_code', 'barcode']:
                                display_sku = meta.get('value')
                                break
                    if not display_sku:
                        display_sku = "ללא"

                    # נתונים נוספים
                    price = p.get('price', '') + " שח"
                    stock = "במלאי" if p.get('stock_status') == 'instock' else "חסר"
                    
                    # ניקוי תיאור
                    raw_desc = str(p.get('short_description', '')) + " " + str(p.get('description', ''))
                    clean_desc = raw_desc.replace('<p>', '').replace('</p>', '').replace('<br>', '\n').strip()
                    if len(clean_desc) > 300: clean_desc = clean_desc[:300] + "..."

                    # פורמט הבלוק
                    content += f"--- מוצר ---\n"
                    content += f"ID: {system_id}\n"
                    content += f"SKU: {display_sku}\n" # תווית ברורה ל-AI
                    content += f"שם: {name}\n"
                    content += f"מחיר: {price}\n"
                    content += f"מלאי: {stock}\n"
                    content += f"תיאור: {clean_desc}\n"
                    content += f"------------\n\n"
            else:
                content = "No products found."

            file_path = "/tmp/catalog.txt"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            # --- 3. עדכון OpenAI (כולל מחיקת הישן) ---
            client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            assistant_id = os.environ.get("OPENAI_ASSISTANT_ID")
            
            my_assistant = client.beta.assistants.retrieve(assistant_id)
            tool_res = my_assistant.tool_resources
            
            vs_id = None
            
            # איתור ה-Vector Store הקיים
            if tool_res and tool_res.file_search and tool_res.file_search.vector_store_ids:
                vs_id = tool_res.file_search.vector_store_ids[0]
                
                # --- ניקוי: מחיקת קבצים ישנים מהחנות ---
                # זה השלב הקריטי שמונע כפילויות!
                existing_files = client.beta.vector_stores.files.list(vector_store_id=vs_id)
                for file in existing_files:
                    try:
                        client.beta.vector_stores.files.delete(vector_store_id=vs_id, file_id=file.id)
                    except:
                        pass # מתעלמים משגיאות מחיקה בודדות
            else:
                # יצירה חדשה אם אין
                vs = client.beta.vector_stores.create(name="ShopiPet Store")
                vs_id = vs.id
                client.beta.assistants.update(
                    assistant_id=assistant_id,
                    tool_resources={"file_search": {"vector_store_ids": [vs_id]}}
                )

            # העלאת הקובץ החדש והנקי
            with open(file_path, "rb") as f:
                client.beta.vector_stores.files.upload_and_poll(
                    vector_store_id=vs_id,
                    file=f
                )

            response_data = {
                "status": "success",
                "message": "Catalog synced & Cleaned (Old files removed)",
                "products_count": len(products) if products else 0,
                "vector_store_id": vs_id
            }

        except Exception as e:
            print(f"ERROR: {traceback.format_exc()}")
            response_data = {
                "status": "error",
                "error": str(e),
                "location": "Handler Logic"
            }

        self.wfile.write(json.dumps(response_data).encode('utf-8'))
