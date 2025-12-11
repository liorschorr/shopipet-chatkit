from http.server import BaseHTTPRequestHandler
import json
import os
from woocommerce import API
from utils.ai import get_embedding
from utils.db import save_catalog

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # 1. חיבור ל-WooCommerce
            wcapi = API(
                url=os.environ.get("WC_URL"),
                consumer_key=os.environ.get("WC_CONSUMER_KEY"),
                consumer_secret=os.environ.get("WC_CONSUMER_SECRET"),
                version="wc/v3",
                timeout=50
            )

            processed_catalog = []
            page = 1
            
            while True:
                products = wcapi.get("products", params={"per_page": 100, "page": page}).json()
                if not products:
                    break
                
                for p in products:
                    if p['status'] != 'publish':
                        continue

                    # עיבוד מחיר ומבצע
                    price_str = f"{p['price']} ₪"
                    if p['on_sale']:
                        price_str = f"מבצע: {p['sale_price']} ₪ (במקום {p['regular_price']} ₪)"

                    # עיבוד מלאי
                    stock_str = "במלאי" if p['stock_status'] == 'instock' else "חסר במלאי"

                    # עיבוד וריאציות
                    variations_str = ""
                    if p['type'] == 'variable':
                        attrs = []
                        for attr in p['attributes']:
                            options = ", ".join(attr['options'])
                            attrs.append(f"{attr['name']}: {options}")
                        variations_str = " | אפשרויות: " + " ; ".join(attrs)

                    # תגיות וקטגוריות
                    cats = ", ".join([c['name'] for c in p['categories']])
                    tags = ", ".join([t['name'] for t in p['tags']])
                    
                    clean_desc = p['short_description'].replace('<p>', '').replace('</p>', '')

                    # הטקסט המלא ל-AI
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

            save_catalog(processed_catalog)
            
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success", "items": len(processed_catalog)}).encode('utf-8'))

        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
