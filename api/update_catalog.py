from http.server import BaseHTTPRequestHandler
import json
import os
from woocommerce import API
from utils.ai import get_embedding
from utils.db import save_catalog

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # הגדרה: כמה מוצרים למשוך בריצה הזו? (5 לבדיקה מהירה)
            MAX_PRODUCTS_TO_PROCESS = 5 
            
            wcapi = API(
                url=os.environ.get("WOO_BASE_URL"),
                consumer_key=os.environ.get("WOO_CONSUMER_KEY"),
                consumer_secret=os.environ.get("WOO_CONSUMER_SECRET"),
                version="wc/v3",
                timeout=20 
            )

            processed_catalog = []
            page = 1
            
            # לולאה ראשית
            while len(processed_catalog) < MAX_PRODUCTS_TO_PROCESS:
                # מושכים רק 10 מוצרים בכל קריאה כדי לא להעמיס
                products = wcapi.get("products", params={"per_page": 10, "page": page}).json()
                
                if not products:
                    break
                
                for p in products:
                    # אם הגענו למכסה - עוצרים מיד
                    if len(processed_catalog) >= MAX_PRODUCTS_TO_PROCESS:
                        break

                    if p['status'] != 'publish':
                        continue

                    # עיבוד נתונים
                    price_str = f"{p['price']} ₪"
                    if p['on_sale']:
                        price_str = f"מבצע: {p['sale_price']} ₪ (במקום {p['regular_price']} ₪)"

                    stock_str = "במלאי" if p['stock_status'] == 'instock' else "חסר במלאי"

                    variations_str = ""
                    if p['type'] == 'variable':
                        attrs = []
                        for attr in p['attributes']:
                            options = ", ".join(attr['options'])
                            attrs.append(f"{attr['name']}: {options}")
                        variations_str = " | אפשרויות: " + " ; ".join(attrs)

                    cats = ", ".join([c['name'] for c in p['categories']])
                    tags = ", ".join([t['name'] for t in p['tags']])
                    clean_desc = p['short_description'].replace('<p>', '').replace('</p>', '')

                    text_to_embed = (
                        f"מוצר: {p['name']}.\n"
                        f"קטגוריה: {cats}.\n"
                        f"מחיר: {price_str}.\n"
                        f"סטטוס: {stock_str}.\n"
                        f"תיאור: {clean_desc}.\n"
                        f"תכונות: {variations_str}.\n"
                        f"תגיות: {tags}."
                    )

                    item = {
                        "id": p['id'],
                        "name": p['name'],
                        "price": p['price'],
                        "link": p['permalink'],
                        "image": p['images'][0]['src'] if p['images'] else "",
                        "embedding": get_embedding(text_to_embed),
                        "raw_text": text_to_embed
                    }
                    processed_catalog.append(item)
                
                page += 1

            # שמירה ל-Redis
            save_catalog(processed_catalog)
            
            self.send_response(200)
            self.end_headers()
            success_msg = {
                "status": "success", 
                "message": "TEST MODE: Processed first 5 items only",
                "items_count": len(processed_catalog)
            }
            self.wfile.write(json.dumps(success_msg).encode('utf-8'))

        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
