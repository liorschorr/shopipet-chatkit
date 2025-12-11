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
                # משיכת מוצרים בפייג'ינג (100 בכל פעם)
                products = wcapi.get("products", params={"per_page": 100, "page": page}).json()
                if not products:
                    break
                
                for p in products:
                    # דילוג על מוצרים לא מפורסמים
                    if p['status'] != 'publish':
                        continue

                    # -- בניית המידע העשיר --
                    
                    # 1. מחיר ומבצע
                    price_str = f"{p['price']} ₪"
                    if p['on_sale']:
                        price_str = f"מבצע: {p['sale_price']} ₪ (במקום {p['regular_price']} ₪)"

                    # 2. מלאי
                    stock_str = "במלאי" if p['stock_status'] == 'instock' else "חסר במלאי"

                    # 3. טיפול בוריאציות (למשל: משקל)
                    variations_str = ""
                    if p['type'] == 'variable':
                        # בונים מחרוזת של האפשרויות, למשל: "משקלים זמינים: 3קג, 12קג"
                        attrs = []
                        for attr in p['attributes']:
                            options = ", ".join(attr['options'])
                            attrs.append(f"{attr['name']}: {options}")
                        variations_str = " | אפשרויות: " + " ; ".join(attrs)

                    # 4. תגיות וקטגוריות
                    cats = ", ".join([c['name'] for c in p['categories']])
                    tags = ", ".join([t['name'] for t in p['tags']])
                    
                    # 5. ניקוי HTML מהתיאור
                    clean_desc = p['short_description'].replace('<p>', '').replace('</p>', '')

                    # יצירת הטקסט המלא ל-Embedding (מה שה-AI יקרא)
                    # אנו בונים זאת כטקסט טבעי כדי שהמודל יבין את ההקשר
                    text_to_embed = (
                        f"מוצר: {p['name']}.\n"
                        f"קטגוריה: {cats}.\n"
                        f"מחיר: {price_str}.\n"
                        f"סטטוס: {stock_str}.\n"
                        f"תיאור: {clean_desc}.\n"
                        f"תכונות: {variations_str}.\n"
                        f"תגיות: {tags}."
                    )

                    # יצירת מטא-דאטה (מה שנחזיר לצ'אט כדי להציג קישור/תמונה)
                    item = {
                        "id": p['id'],
                        "name": p['name'],
                        "price": p['price'],
                        "link": p['permalink'],
                        "image": p['images'][0]['src'] if p['images'] else "",
                        "embedding": get_embedding(text_to_embed), # קריאה ל-OpenAI
                        "raw_text": text_to_embed # שומרים את הטקסט הגולמי לשימוש בקונטקסט
                    }
                    processed_catalog.append(item)

                page += 1

            # שמירה ב-Redis
            save_catalog(processed_catalog)
            
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success", "items": len(processed_catalog)}).encode('utf-8'))

        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
