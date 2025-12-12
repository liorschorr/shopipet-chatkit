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
                raise Exception(f"CRITICAL: Libraries missing. {e}")

            # --- בדיקת משתנים ---
            required_vars = ["OPENAI_API_KEY", "OPENAI_ASSISTANT_ID", "WOO_BASE_URL", "WOO_CONSUMER_KEY", "WOO_CONSUMER_SECRET"]
            missing = [var for var in required_vars if not os.environ.get(var)]
            if missing:
                raise Exception(f"Missing Env Vars: {', '.join(missing)}")

            # --- 1. משיכת מוצרים ---
            wcapi = API(
                url=os.environ.get("WOO_BASE_URL"),
                consumer_key=os.environ.get("WOO_CONSUMER_KEY"),
                consumer_secret=os.environ.get("WOO_CONSUMER_SECRET"),
                version="wc/v3",
                timeout=60
            )
            
            products_res = wcapi.get("products", params={"per_page": 100, "status": "publish"})
            products = products_res.json()
            
            # --- 2. עיבוד הנתונים ---
            content = ""
            if products:
                for p in products:
                    # מזהה פנימי סודי (משמש רק לפונקציות טכניות)
                    system_id = p.get('id')
                    
                    # --- לוגיקה לאיחוד מק"טים וברקודים ---
                    # יוצרים רשימה (Set) כדי למנוע כפילויות
                    identifiers = set()
                    
                    # 1. הוספת ה-SKU הראשי
                    if p.get('sku'):
                        identifiers.add(str(p.get('sku')))
                    
                    # 2. הוספת GTIN/EAN/UPC מתוך Meta Data
                    for meta in p.get('meta_data', []):
                        key = meta.get('key', '').lower()
                        # בדיקה רחבה יותר של שדות ברקוד אפשריים
                        if any(k in key for k in ['gtin', 'ean', 'isbn', 'upc', 'barcode']):
                            val = meta.get('value')
                            if val:
                                identifiers.add(str(val))
                    
                    # המרת הרשימה למחרוזת נקייה (מופרדת בפסיקים)
                    if identifiers:
                        codes_display = ", ".join(identifiers)
                    else:
                        codes_display = "ללא"

                    name = p.get('name', 'N/A')
                    link = p.get('permalink', '')
                    
                    # מחירים
                    price = str(p.get('price', '')) + " שח"
                    stock = "במלאי" if p.get('stock_status') == 'instock' else "חסר"
                    
                    # ניקוי תיאור
                    raw_desc = str(p.get('short_description', '')) + " " + str(p.get('description', ''))
                    clean_desc = raw_desc.replace('<p>', '').replace('</p>', '').replace('<br>', '\n').strip()
                    if len(clean_desc) > 300: clean_desc = clean_desc[:300] + "..."

                    # --- בניית הבלוק ל-AI ---
                    content += f"--- מוצר ---\n"
                    # שים לב להערה ל-AI ליד ה-ID
                    content += f"System_ID: {system_id} (INTERNAL_USE_ONLY)\n"
                    # כל המספרים בשורה אחת
                    content += f"מזהים (מק\"ט/ברקוד): {codes_display}\n"
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

            # --- 3. עדכון OpenAI וניקוי ישן ---
            client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            assistant_id = os.environ.get("OPENAI_ASSISTANT_ID")
            
            my_assistant = client.beta.assistants.retrieve(assistant_id)
            tool_res = my_assistant.tool_resources
            
            vs_id = None
            if tool_res and tool_res.file_search and tool_res.file_search.vector_store_ids:
                vs_id = tool_res.file_search.vector_store_ids[0]
                # מחיקת קבצים ישנים למניעת בלבול
                for file in client.beta.vector_stores.files.list(vector_store_id=vs_id):
                    try:
                        client.beta.vector_stores.files.delete(vector_store_id=vs_id, file_id=file.id)
                    except: pass
            else:
                vs = client.beta.vector_stores.create(name="ShopiPet Store")
                vs_id = vs.id
                client.beta.assistants.update(
                    assistant_id=assistant_id,
                    tool_resources={"file_search": {"vector_store_ids": [vs_id]}}
                )

            with open(file_path, "rb") as f:
                client.beta.vector_stores.files.upload_and_poll(vector_store_id=vs_id, file=f)

            response_data = {
                "status": "success",
                "message": "Catalog Synced (Merged Identifiers)",
                "products_count": len(products),
                "preview_sample": content[:400]
            }

        except Exception as e:
            print(f"ERROR: {traceback.format_exc()}")
            response_data = {"status": "error", "error": str(e)}

        self.wfile.write(json.dumps(response_data).encode('utf-8'))
