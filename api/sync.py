from http.server import BaseHTTPRequestHandler
import json
import os
import traceback

# פונקציה פנימית לקידוד מכירות
def get_sales_rank(sales_count):
    if sales_count >= 20:
        return "מוביל"
    elif sales_count >= 5:
        return "מבוקש"
    else:
        return "רגיל"

# פונקציה פנימית לקידוד מצב המלאי (הלוגיקה הקבועה)
def get_stock_status_text(stock_quantity, status_tag):
    if status_tag != 'instock':
        return "אזל מהמלאי"
    
    if stock_quantity is None or stock_quantity > 3:
        return "במלאי"
    elif stock_quantity >= 1:
        # זהו הנוסח המקודד: ה-AI יצטרך לקרוא את זה ולהשתמש בו
        return f"מלאי נמוך (נותרו רק {int(stock_quantity)} יחידות, כדאי להזדרז להזמין!)"
    else:
        return "אזל מהמלאי"


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        response_data = {}

        try:
            from openai import OpenAI
            from woocommerce import API

            # ... [בדיקות משתנים ו-WooCommerce API] ...
            required_vars = ["OPENAI_API_KEY", "OPENAI_ASSISTANT_ID", "WOO_BASE_URL", "WOO_CONSUMER_KEY", "WOO_CONSUMER_SECRET"]
            missing = [var for var in required_vars if not os.environ.get(var)]
            if missing:
                raise Exception(f"Missing Env Vars: {', '.join(missing)}")

            wcapi = API(
                url=os.environ.get("WOO_BASE_URL"),
                consumer_key=os.environ.get("WOO_CONSUMER_KEY"),
                consumer_secret=os.environ.get("WOO_CONSUMER_SECRET"),
                version="wc/v3",
                timeout=60
            )
            
            # מסננים רק מוצרים שפורסמו (status: publish)
            products_res = wcapi.get("products", params={"per_page": 100, "status": "publish"})
            if products_res.status_code != 200:
                 raise Exception(f"WooCommerce Error {products_res.status_code}: {products_res.text}")
                 
            products = products_res.json()
            
            # --- עיבוד הנתונים לקובץ טקסט אופטימלי ---
            content = ""
            for p in products:
                system_id = p.get('id')
                name = p.get('name', 'N/A')
                
                # --- 1. מזהים (מק"ט/ברקוד) ---
                identifiers = set()
                if p.get('sku'): identifiers.add(str(p.get('sku')))
                for meta in p.get('meta_data', []):
                    key = meta.get('key', '').lower()
                    if any(k in key for k in ['gtin', 'ean', 'isbn', 'upc', 'barcode']):
                        val = meta.get('value')
                        if val: identifiers.add(str(val))
                codes_display = ", ".join(identifiers) if identifiers else "ללא"
                
                # --- 2. מחירים ומבצעים ---
                price = str(p.get('price', '')) + " שח"
                sale_end_date = p.get('date_on_sale_to', '')
                
                # --- 3. מלאי (קידוד הלוגיקה כאן!) ---
                stock_status_text = get_stock_status_text(p.get('stock_quantity'), p.get('stock_status'))
                
                # --- 4. שדות נוספים ---
                weight_val = p.get('weight', '0')
                if float(weight_val) < 1.0 and p.get('weight_unit') == 'kg':
                    weight_display = f"{float(weight_val) * 1000} גרם"
                else:
                    weight_display = f"{weight_val} קילוגרם"

                categories = ", ".join([c['name'] for c in p.get('categories', [])])
                brands = ", ".join([b['name'] for b in p.get('brands', [])])
                tags = ", ".join([t['name'] for t in p.get('tags', [])])
                sales_rank = get_sales_rank(p.get('total_sales', 0))
                
                # --- 5. מאפיינים מפורטים (Attributes) ---
                attributes_list = []
                for attr in p.get('attributes', []):
                    opts = ", ".join(attr.get('options', []))
                    attributes_list.append(f"{attr.get('name')}: {opts}")
                attributes_str = " | ".join(attributes_list)
                
                # --- 6. תיאור נקי ---
                raw_desc = str(p.get('short_description', '')).replace('<p>', '').replace('</p>', '').strip()
                if len(raw_desc) > 300: raw_desc = raw_desc[:300] + "..."
                
                # --- 7. בניית הבלוק ל-AI ---
                content += f"--- מוצר ---\n"
                content += f"System_ID: {system_id} (INTERNAL_USE_ONLY)\n"
                content += f"מזהים (מק\"ט/ברקוד): {codes_display}\n"
                content += f"שם: {name}\n"
                content += f"מותג: {brands}\n"
                content += f"קטגוריות: {categories}\n"
                content += f"תגיות: {tags}\n"
                content += f"מאפיינים: {attributes_str}\n"
                content += f"מחיר: {price}\n"
                if p.get('on_sale'):
                    content += f"מצב מבצע: {p.get('sale_price')} שח (מחיר רגיל: {p.get('regular_price')} שח)\n"
                    if sale_end_date:
                        content += f"תוקף מבצע עד: {sale_end_date}\n"
                content += f"משקל: {weight_display}\n"
                content += f"מצב מלאי: {stock_status_text}\n" # הפלט המקודד
                content += f"דירוג מכירות: {sales_rank}\n"
                content += f"תיאור קצר: {raw_desc}\n"
                content += f"קישור (פנימי): /?p={system_id}\n"
                content += f"------------\n\n"

            file_path = "/tmp/catalog.txt"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            # --- העלאה ל-OpenAI (כולל ניקוי) ---
            client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            assistant_id = os.environ.get("OPENAI_ASSISTANT_ID")
            my_assistant = client.beta.assistants.retrieve(assistant_id)
            tool_res = my_assistant.tool_resources
            
            vs_id = None
            if tool_res and tool_res.file_search and tool_res.file_search.vector_store_ids:
                vs_id = tool_res.file_search.vector_store_ids[0]
                for file in client.beta.vector_stores.files.list(vector_store_id=vs_id):
                    try: client.beta.vector_stores.files.delete(vector_store_id=vs_id, file_id=file.id)
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

            response_data = {"status": "success", "message": "Catalog Synced with final logic."}

        except Exception as e:
            response_data = {"status": "error", "error": str(e), "trace": traceback.format_exc()}

        self.wfile.write(json.dumps(response_data).encode('utf-8'))
