from http.server import BaseHTTPRequestHandler
import json
import os
import traceback

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # כותרות תגובה למניעת Timeout
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
                timeout=60 # הארכתי מעט כי המידע עשיר יותר
            )
            
            # מושכים 100 מוצרים
            products_res = wcapi.get("products", params={"per_page": 100, "status": "publish"})
            
            if products_res.status_code != 200:
                 raise Exception(f"WooCommerce Error {products_res.status_code}: {products_res.text}")
                 
            products = products_res.json()
            
            # --- 2. עיבוד הנתונים לקובץ טקסט עשיר ---
            content = ""
            if products:
                for p in products:
                    # זיהוי בסיסי
                    p_id = p.get('id')
                    sku = p.get('sku', 'N/A')
                    name = p.get('name', 'N/A')
                    link = p.get('permalink', '')
                    
                    # פופולריות ודירוג (Social Proof)
                    rating = p.get('average_rating', '0')
                    rating_count = p.get('rating_count', 0)
                    total_sales = p.get('total_sales', 0)
                    
                    social_proof = ""
                    if float(rating) > 0:
                        social_proof = f"דירוג: {rating}/5 (מתוך {rating_count} מדרגים)"
                    if isinstance(total_sales, int) and total_sales > 10:
                        social_proof += f" | נמכר {total_sales} פעמים (מוצר פופולרי)"

                    # מחירים ומבצעים
                    regular_price = p.get('regular_price', '')
                    sale_price = p.get('sale_price', '')
                    on_sale = p.get('on_sale', False)
                    date_on_sale_to = p.get('date_on_sale_to', '') 

                    price_display = f"{regular_price} שח"
                    if on_sale and sale_price:
                        price_display = f"מבצע: {sale_price} שח (במקום {regular_price})"
                        if date_on_sale_to:
                            price_display += f" - עד {date_on_sale_to}"

                    # מלאי
                    stock_status = "במלאי" if p.get('stock_status') == 'instock' else "חסר במלאי"
                    
                    # קטגוריות ותגיות (חשוב מאוד לסינון)
                    categories = ", ".join([c['name'] for c in p.get('categories', [])])
                    tags = ", ".join([t['name'] for t in p.get('tags', [])])
                    
                    # מאפיינים (Attributes)
                    attributes_list = []
                    for attr in p.get('attributes', []):
                        opts = ", ".join(attr.get('options', []))
                        attributes_list.append(f"{attr.get('name')}: {opts}")
                    attributes_str = " | ".join(attributes_list)

                    # ניקוי תיאור
                    raw_desc = str(p.get('short_description', '')) + " " + str(p.get('description', ''))
                    clean_desc = raw_desc.replace('<p>', '').replace('</p>', '').replace('<br>', '\n').replace('&nbsp;', ' ').strip()
                    if len(clean_desc) > 350: # שומרים יותר טקסט כי התיאור חשוב
                        clean_desc = clean_desc[:350] + "..."

                    # --- בניית הבלוק למוצר (הפורמט שה-AI קורא) ---
                    content += f"--- מוצר ---\n"
                    content += f"ID: {p_id}\n"
                    content += f"SKU (מק\"ט): {sku}\n"
                    content += f"שם: {name}\n"
                    content += f"קטגוריות: {categories}\n"
                    if tags:
                        content += f"תגיות (מידע חשוב): {tags}\n"
                    content += f"מחיר: {price_display}\n"
                    content += f"מצב מלאי: {stock_status}\n"
                    if social_proof:
                        content += f"פופולריות: {social_proof}\n"
                    if attributes_str:
                        content += f"מאפיינים: {attributes_str}\n"
                    content += f"תיאור: {clean_desc}\n"
                    content += f"קישור: {link}\n"
                    content += f"------------\n\n"

            else:
                content = "No products found in store."

            # שמירה לקובץ זמני
            file_path = "/tmp/catalog.txt"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            # --- 3. העלאה ל-OpenAI ---
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
                "message": "Full Rich Catalog Sync Completed",
                "products_count": len(products) if products else 0,
                "vector_store_id": vs_id
            }

        except Exception as e:
            print(f"ERROR: {traceback.format_exc()}")
            response_data = {
                "status": "error",
                "error": str(e),
                "location": "Inside Handler Logic"
            }

        self.wfile.write(json.dumps(response_data).encode('utf-8'))
