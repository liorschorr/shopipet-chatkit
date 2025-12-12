from http.server import BaseHTTPRequestHandler
import json
import os
import traceback

# --- פונקציות עזר מוגנות ---

def safe_int(val, default=0):
    """ממיר בבטחה למספר שלם"""
    try:
        if val is None: return default
        return int(float(val)) # מטפל גם ב-"5.0"
    except (ValueError, TypeError):
        return default

def safe_float(val, default=0.0):
    """ממיר בבטחה למספר עשרוני"""
    try:
        if not val: return default
        return float(val)
    except (ValueError, TypeError):
        return default

def get_sales_rank(sales_count):
    count = safe_int(sales_count)
    if count >= 20: return "מוביל (רב מכר 🔥)"
    elif count >= 5: return "מבוקש"
    return "רגיל"

def get_stock_status_text(stock_quantity, status_tag):
    # קודם כל בודקים את התגית הראשי
    if status_tag != 'instock':
        return "אזל מהמלאי"
    
    # אם כמות המלאי היא None (לא מנוהל) - זה נחשב שיש מלאי
    if stock_quantity is None:
        return "במלאי"
        
    qty = safe_int(stock_quantity)
    
    if qty > 3:
        return "במלאי"
    elif qty >= 1:
        return f"מלאי נמוך (נותרו רק {qty} יחידות, כדאי להזדרז! 🏃‍♂️)"
    else:
        # מצב מוזר: instock אבל כמות 0
        return "אזל מהמלאי"

# --- השרת ---

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        response_data = {}

        try:
            from openai import OpenAI
            from woocommerce import API

            # בדיקת משתנים
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
            
            # משיכת מוצרים
            products_res = wcapi.get("products", params={"per_page": 100, "status": "publish"})
            if products_res.status_code != 200:
                 raise Exception(f"WooCommerce Error {products_res.status_code}: {products_res.text}")
                 
            products = products_res.json()
            
            # --- עיבוד הנתונים ---
            content = ""
            for p in products:
                system_id = p.get('id')
                name = p.get('name', 'N/A')
                
                # מזהים
                identifiers = set()
                if p.get('sku'): identifiers.add(str(p.get('sku')))
                for meta in p.get('meta_data', []):
                    key = str(meta.get('key', '')).lower()
                    if any(k in key for k in ['gtin', 'ean', 'isbn', 'upc', 'barcode']):
                        val = meta.get('value')
                        if val: identifiers.add(str(val))
                codes_display = ", ".join(identifiers) if identifiers else "ללא"
                
                # מחיר
                price_str = f"{p.get('price', '0')} ₪"
                sale_info = ""
                if p.get('on_sale'):
                    reg = p.get('regular_price', '')
                    sale = p.get('sale_price', '')
                    date_to = p.get('date_on_sale_to', '')
                    sale_info = f"מבצע: {sale} ₪ (במקום {reg} ₪)"
                    if date_to: sale_info += f" - בתוקף עד {date_to}"
                
                # מלאי - שימוש בפונקציה המוגנת
                stock_display = get_stock_status_text(p.get('stock_quantity'), p.get('stock_status'))
                
                # משקל - שימוש בפונקציה המוגנת
                w_float = safe_float(p.get('weight'))
                if w_float > 0 and w_float < 1.0:
                    weight_display = f"{int(w_float * 1000)} גרם"
                elif w_float >= 1.0:
                    weight_display = f"{w_float} ק\"ג"
                else:
                    weight_display = ""

                # טקסטים
                categories = ", ".join([c['name'] for c in p.get('categories', [])])
                tags = ", ".join([t['name'] for t in p.get('tags', [])])
                
                brands_list = [b['name'] for b in p.get('brands', [])]
                if not brands_list:
                     for meta in p.get('meta_data', []):
                         if 'brand' in str(meta.get('key', '')).lower():
                             brands_list.append(str(meta.get('value')))
                brand_display = ", ".join(brands_list)

                sales_rank = get_sales_rank(p.get('total_sales'))
                
                # מאפיינים
                attributes_list = []
                for attr in p.get('attributes', []):
                    opts = ", ".join(attr.get('options', []))
                    attributes_list.append(f"{attr.get('name')}: {opts}")
                attributes_str = " | ".join(attributes_list)
                
                # תיאור
                raw_desc = str(p.get('short_description', '')) + " " + str(p.get('description', ''))
                clean_desc = raw_desc.replace('<p>', '').replace('</p>', '').replace('<br>', '\n').replace('&nbsp;', ' ').strip()
                if len(clean_desc) > 400: clean_desc = clean_desc[:400] + "..."
                
                # --- הרכבת הבלוק ---
                content += f"--- מוצר ---\n"
                content += f"System_ID: {system_id} (INTERNAL)\n"
                content += f"מזהים (מק\"ט/ברקוד): {codes_display}\n"
                content += f"שם: {name}\n"
                if brand_display: content += f"מותג: {brand_display}\n"
                content += f"קטגוריות: {categories}\n"
                if tags: content += f"תגיות: {tags}\n"
                if attributes_str: content += f"מאפיינים: {attributes_str}\n"
                
                content += f"מחיר: {price_str}\n"
                if sale_info: content += f"{sale_info}\n"
                
                if weight_display: content += f"משקל: {weight_display}\n"
                content += f"מצב מלאי: {stock_display}\n"
                content += f"פופולריות: {sales_rank}\n"
                content += f"תיאור: {clean_desc}\n"
                content += f"קישור ישיר: /?p={system_id}\n"
                content += f"------------\n\n"

            file_path = "/tmp/catalog.txt"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            # --- העלאה ל-OpenAI ---
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

            response_data = {
                "status": "success",
                "message": "Catalog Synced Successfully (Safe Mode)",
                "products_count": len(products),
                "vector_store_id": vs_id
            }

        except Exception as e:
            # תפיסת השגיאה והצגתה למשתמש במקום קריסת שרת
            print(f"CRITICAL SYNC ERROR: {traceback.format_exc()}")
            response_data = {
                "status": "error",
                "error": str(e),
                "trace": traceback.format_exc()
            }

        self.wfile.write(json.dumps(response_data).encode('utf-8'))
