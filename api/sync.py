from http.server import BaseHTTPRequestHandler
import json
import os
import traceback
from datetime import datetime

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        response_data = {}
        start_time = datetime.now()

        try:
            # --- טעינת ספריות ---
            try:
                from openai import OpenAI
                from woocommerce import API
            except ImportError as e:
                raise Exception(f"CRITICAL: Failed to import libraries. Details: {e}")

            # --- בדיקת כל משתני הסביבה ---
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

            # --- 1. משיכת כל המוצרים מ-WooCommerce ---
            wcapi = API(
                url=os.environ.get("WOO_BASE_URL"),
                consumer_key=os.environ.get("WOO_CONSUMER_KEY"),
                consumer_secret=os.environ.get("WOO_CONSUMER_SECRET"),
                version="wc/v3",
                timeout=60
            )
            
            all_products = []
            page = 1
            
            while True:
                products_res = wcapi.get("products", params={
                    "per_page": 100,
                    "page": page,
                    "status": "publish"
                })
                
                if products_res.status_code != 200:
                    raise Exception(f"WooCommerce Error {products_res.status_code}: {products_res.text}")
                
                batch = products_res.json()
                if not batch:
                    break
                    
                all_products.extend(batch)
                page += 1
            
            # --- 2. יצירת קובץ הקטלוג ---
            content = f"# קטלוג מוצרים - עודכן: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            
            if all_products:
                for p in all_products:
                    name = p.get('name', 'N/A')
                    price = p.get('price', '0')
                    regular_price = p.get('regular_price', '')
                    sale_price = p.get('sale_price', '')
                    link = p.get('permalink', '')
                    sku = p.get('sku', '')
                    stock = p.get('stock_status', 'unknown')
                    
                    # ניקוי תיאור מתגיות HTML
                    desc = str(p.get('short_description', ''))
                    for tag in ['<p>', '</p>', '<br>', '<br/>', '<strong>', '</strong>']:
                        desc = desc.replace(tag, ' ')
                    desc = ' '.join(desc.split()).strip()
                    
                    # קטגוריות
                    categories = ', '.join([c.get('name', '') for c in p.get('categories', [])])
                    
                    content += f"---\n"
                    content += f"מוצר: {name}\n"
                    content += f"מק״ט: {sku}\n" if sku else ""
                    content += f"מחיר: ₪{price}\n"
                    if sale_price and regular_price:
                        content += f"מחיר מקורי: ₪{regular_price} (במבצע!)\n"
                    content += f"מלאי: {'במלאי' if stock == 'instock' else 'אזל'}\n"
                    content += f"קטגוריות: {categories}\n" if categories else ""
                    content += f"תיאור: {desc}\n" if desc else ""
                    content += f"קישור: {link}\n\n"
            else:
                content += "לא נמצאו מוצרים בחנות.\n"

            file_path = "/tmp/catalog.txt"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            # --- 3. OpenAI - ניהול Vector Store ---
            client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            assistant_id = os.environ.get("OPENAI_ASSISTANT_ID")
            
            my_assistant = client.beta.assistants.retrieve(assistant_id)
            tool_res = my_assistant.tool_resources
            
            vs_id = None
            vs_created = False
            
            if tool_res and tool_res.file_search and tool_res.file_search.vector_store_ids:
                vs_id = tool_res.file_search.vector_store_ids[0]
            else:
                vs = client.beta.vector_stores.create(name="ShopiPet Catalog")
                vs_id = vs.id
                vs_created = True
                client.beta.assistants.update(
                    assistant_id=assistant_id,
                    tool_resources={"file_search": {"vector_store_ids": [vs_id]}}
                )

            # --- 4. מחיקת קבצים ישנים ---
            deleted_count = 0
            if not vs_created:
                try:
                    existing_files = client.beta.vector_stores.files.list(vector_store_id=vs_id)
                    for file in existing_files.data:
                        try:
                            client.beta.vector_stores.files.delete(
                                vector_store_id=vs_id,
                                file_id=file.id
                            )
                            client.files.delete(file.id)
                            deleted_count += 1
                        except Exception:
                            pass
                except Exception:
                    pass

            # --- 5. העלאת הקובץ החדש ---
            with open(file_path, "rb") as f:
                uploaded_file = client.beta.vector_stores.files.upload_and_poll(
                    vector_store_id=vs_id,
                    file=f
                )

            duration = (datetime.now() - start_time).total_seconds()

            response_data = {
                "status": "success",
                "message": "Sync completed successfully",
                "timestamp": datetime.now().isoformat(),
                "stats": {
                    "products_synced": len(all_products),
                    "pages_fetched": page - 1,
                    "old_files_deleted": deleted_count,
                    "duration_seconds": round(duration, 2)
                },
                "vector_store": {
                    "id": vs_id,
                    "newly_created": vs_created
                }
            }

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            print(f"ERROR: {traceback.format_exc()}")
            response_data = {
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "duration_seconds": round(duration, 2),
                "traceback": traceback.format_exc()
            }

        response_json = json.dumps(response_data, ensure_ascii=False, indent=2)
        self.wfile.write(response_json.encode('utf-8'))
