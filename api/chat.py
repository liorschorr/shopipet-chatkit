from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
import json
import os
import re

# Import Google Sheets
try:
    from googleapiclient.discovery import build
    from google.oauth2 import service_account
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    print("Warning: Google API not available")

# Import OpenAI
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("Warning: OpenAI not available")

# === Create Flask app ===
app = Flask(__name__)
CORS(app)

# === Configuration ===
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "1-XfEIXT0ovbhkWnBezc4v2xIcmUdONC7mAcep9554q8")
SHEET_RANGE = os.environ.get("SHEET_RANGE", "Sheet1!A2:R")
GOOGLE_CREDENTIALS = os.environ.get("GOOGLE_CREDENTIALS")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Initialize clients
creds = None
openai_client = None

# Initialize Google Sheets
if GOOGLE_AVAILABLE and GOOGLE_CREDENTIALS:
    try:
        service_account_info = json.loads(GOOGLE_CREDENTIALS)
        creds = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        print("✅ Google Sheets initialized")
    except Exception as e:
        print(f"❌ Google credentials error: {e}")

# Initialize OpenAI
if OPENAI_AVAILABLE and OPENAI_API_KEY:
    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        print("✅ OpenAI initialized")
    except Exception as e:
        print(f"❌ OpenAI error: {e}")

# === SYNONYMS AND SEARCH ENHANCEMENT ===
SYNONYMS = {
    'כלב': ['כלבים', 'דוג', 'דוגי', 'כלבלב', 'puppy', 'dog', 'dogs'],
    'חתול': ['חתולים', 'קיטי', 'חתולון', 'חתלתול', 'cat', 'kitten', 'cats'],
    'גור': ['גורים', 'גור כלבים', 'גור חתולים', 'puppies', 'kittens', 'צעיר', 'צעירים', 'גורון', 'גוריה'],
    'ציפור': ['ציפורים', 'bird', 'birds'],
    'דג': ['דגים', 'fish'],
    'מזון': ['אוכל', 'מזונות', 'אוכלים', 'מאכל', 'food', 'אוכלן', 'buy', 'pay', 'purchase', 'acquire'],
    'יבש': ['מזון יבש', 'קיבל', 'dry', 'דראי', 'יבשים'],
    'רטוב': ['מזון רטוב', 'שימורים', 'פחית', 'wet', 'וואט', 'רטובים'],
    'חטיף': ['חטיפים', 'פינוק', 'פינוקים', 'treats', 'snacks', 'נשנושים'],
    'צעצוע': ['צעצועים', 'משחק', 'משחקים', 'toy', 'toys'],
    'חול': ['ליטר', 'חולות', 'litter', 'sand', 'box', 'housing', 'unit', 'package'],
    'מונג': ['מונג׳', 'monge', 'mong', 'מונז', 'מונז׳'],
    'פרופלאן': ['proplan', 'פרו פלאן', 'פרו פלן', 'pro plan', 'pro-plan'],
    'ג׳וסרה': ['גוסרה', 'josera', 'גוזרה', 'ג׳וזרה', 'josra'],
    'הריטג': ['הריטג׳', 'heritage', 'הריטז', 'הריטז׳', 'recipe'],
    'אקאנה': ['אקנה', 'acana', 'akana'],
    'סלמון': ['salmon', 'salomon', 'סלומון'],
    'סנסיטיב': ['סנסטיב', 'sensitive', 'רגיש'],
    'מטאבוליק': ['metabolic', 'מטבוליק', 'מתבוליק'],
    'גדול': ['גדולים', 'לארג', 'large', 'big', 'ענק'],
    'קטן': ['קטנים', 'סמול', 'small', 'mini', 'מיני', 'זעיר'],
    'בינוני': ['בינוניים', 'medium', 'מדיום'],
    'גור': ['גורים', 'צעיר', 'junior', 'puppy', 'kitten', 'צעירים'],
    'בוגר': ['בוגרים', 'adult', 'אדולט'],
    'מבוגר': ['סניור', 'זקן', 'senior', 'aged', 'מבוגרים'],
}

PET_EXCLUSIONS = {
    'כלב': ['חתול', 'חתולים', 'cat', 'cats', 'kitten', 'קיטי', 'חתלתול'],
    'חתול': ['כלב', 'כלבים', 'dog', 'dogs', 'puppy', 'דוג', 'כלבלב'],
    'ציפור': ['כלב', 'חתול', 'dog', 'cat', 'כלבים', 'חתולים'],
    'דג': ['כלב', 'חתול', 'dog', 'cat', 'כלבים', 'חתולים'],
}

def get_pet_type_from_query(query):
    query_lower = query.lower()
    if any(word in query_lower for word in ['גור', 'גורים', 'puppy', 'puppies', 'kitten', 'kittens']):
        if any(word in query_lower for word in ['כלב', 'כלבים', 'dog', 'puppy', 'puppies']):
            return 'כלב'
        elif any(word in query_lower for word in ['חתול', 'חתולים', 'cat', 'kitten', 'kittens']):
            return 'חתול'
        else:
            return 'גור'
    for pet, synonyms in SYNONYMS.items():
        if pet in ['כלב', 'חתול', 'ציפור', 'דג']:
            all_terms = [pet] + synonyms
            if any(term in query_lower for term in all_terms):
                return pet
    return None

def is_pet_related_query(query):
    query_lower = query.lower()
    pet_indicators = [
        'כלב', 'חתול', 'ציפור', 'דג', 'גור', 'dog', 'cat', 'bird', 'fish', 'puppy', 'kitten',
        'כלבים', 'חתולים', 'ציפורים', 'דגים', 'גורים',
        'מזון', 'אוכל', 'צעצוע', 'חול', 'ליטר', 'רצועה', 'קולר', 'כלוב', 'אקווריום',
        'food', 'toy', 'litter', 'collar', 'leash',
        'טיפוח', 'רחצה', 'וטרינר', 'חיסון', 'פרעושים',
        'מונג', 'פרופלאן', 'אקאנה', 'רויאל', 'ג׳וסרה', 'הריטג',
        'monge', 'proplan', 'acana', 'royal', 'josera'
    ]
    return any(indicator in query_lower for indicator in pet_indicators)

def should_exclude_product(product_name, product_category, detected_pet):
    if not detected_pet or detected_pet not in PET_EXCLUSIONS:
        return False
    if detected_pet == 'גור':
        return False
    text_to_check = f"{product_name} {product_category}".lower()
    exclusion_words = PET_EXCLUSIONS[detected_pet]
    for word in exclusion_words:
        if word in text_to_check:
            print(f"⚠️ EXCLUDED: '{product_name}' contains '{word}' (searching for {detected_pet})")
            return True
    return False

def expand_query_with_synonyms(query):
    expanded = [query.lower()]
    words = query.lower().split()
    for word in words:
        for key, synonyms in SYNONYMS.items():
            if word in synonyms or word == key:
                expanded.extend([key] + synonyms)
    return list(set(expanded))

def is_sku_query(query):
    clean = query.replace(' ', '').replace('מק"ט', '').replace('מקט', '')
    return len(clean) > 5 and sum(c.isdigit() for c in clean) > len(clean) * 0.7

def calculate_product_score(product, query_terms, original_query):
    score = 0
    name = product.get('name', '').lower()
    category = product.get('category', '').lower()
    brand = product.get('brand', '').lower()
    desc = product.get('description', '').lower()
    if original_query.lower() in name:
        score += 50
    name_matches = sum(1 for term in query_terms if term in name)
    score += min(name_matches * 10, 35)
    cat_matches = sum(1 for term in query_terms if term in category)
    score += min(cat_matches * 8, 25)
    if any(term in brand for term in query_terms):
        score += 15
    desc_matches = sum(1 for term in query_terms if term in desc)
    score += min(desc_matches * 2, 10)
    if product.get('in_stock', False):
        score += 25
    else:
        score += 5
    if product.get('sale_price'):
        score += 15
        try:
            regular = float(str(product['price']).replace(',', '').replace('₪', '').strip())
            sale = float(str(product['sale_price']).replace(',', '').replace('₪', '').strip())
            if regular > sale:
                discount_pct = (regular - sale) / regular
                score += discount_pct * 5
        except:
            pass
    return score

def fetch_rows():
    if not creds:
        print("⚠️ No credentials for Google Sheets")
        return []
    try:
        service = build("sheets", "v4", credentials=creds)
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=SHEET_RANGE).execute()
        rows = result.get("values", [])
        print(f"✅ Fetched {len(rows)} rows from Google Sheets")
        return rows
    except Exception as e:
        print(f"❌ Error fetching rows: {e}")
        import traceback
        traceback.print_exc()
        return []

def get_llm_response(message, products, context=None):
    if not openai_client:
        return "הנה כמה מוצרים שמצאתי עבורך! 🐾"
    try:
        system_prompt = """אתה שופיבוט (ShopiBot) - עוזר קניות AI של Shopipet.co.il - חנות מוצרים לחיות מחמד.

חשוב מאוד:
- זה חנות לכלבים, חתולים, ציפורים, דגים ומכרסמים - לא לבני אדם!
- "גור" = גור כלב או חתול, לא תינוק אנושי!

חוקים קריטיים:
1. דבר רק בעברית טבעית וחמה
2. תשובות קצרות: 1-2 משפטים בלבד (מקסימום 120 תווים)
3. אל תפרט מוצרים - הם יוצגו בכרטיסים
4. אל תכלול לינקים או מחירים - הם בכרטיסים
5. היה טבעי - אל תגיד "בדקתי במאגר"

דוגמאות טובות:
✅ "מצאתי כמה אפשרויות מעולות לגור שלך! 🐕"
✅ "יש לי המלצות נהדרות לחתולון! 😊"
✅ "הנה בדיוק מה שהכלב שלך צריך! 🎯"

אל תעשה:
❌ "בדקתי במאגר ומצאתי..."
❌ לפרט מוצרים ברשימה
❌ לכלול מחירים או לינקים

תפקידך: הקדמה קצרה וידידותית בלבד."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ]
        if products and len(products) > 0:
            product_hint = f"נמצאו {len(products)} מוצרים רלוונטיים"
            messages.append({"role": "system", "content": product_hint})
        completion = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.8,
            max_tokens=80
        )
        response = completion.choices[0].message.content if completion.choices else "הנה מה שמצאתי! 🐾"
        if len(response) > 150:
            response = response[:147] + "..."
        return response
    except Exception as e:
        print(f"❌ OpenAI error: {e}")
        return "הנה כמה מוצרים מעולים עבורך! 🐾"

# === ROUTES ===

@app.route('/', methods=['GET'])
@app.route('/api', methods=['GET'])
@app.route('/api/ping', methods=['GET'])
def health_check():
    return jsonify({
        "status": "ok",
        "message": "ShopiBot API is running ✅",
        "google_sheets": "connected" if creds else "disconnected",
        "openai": "connected" if openai_client else "disconnected"
    })

@app.route('/api/test-sheets', methods=['GET'])
def test_sheets():
    try:
        rows = fetch_rows()
        sample = None
        if rows:
            r = (rows[0] + [""] * 18)[:18]
            sample = {
                "מזהה": r[0], "שם": r[4], "קטגוריות": r[9],
                "מחיר_רגיל": r[7], "מחיר_מבצע": r[8], 
                "מותג": r[10], "תמונה": r[17]
            }
        return jsonify({
            "status": "ok",
            "rows_count": len(rows),
            "sample_product": sample,
            "spreadsheet_id": SPREADSHEET_ID,
            "sheet_range": SHEET_RANGE
        })
    except Exception as e:
        import traceback
        return jsonify({
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@app.route('/api/chat', methods=['POST', 'OPTIONS'])
def chat():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        req_body = request.get_json() or {}
        message = req_body.get("message", "").strip()
        limit = req_body.get("limit", 5)
        filters = req_body.get("filters", {})
        
        if not message:
            return jsonify({"message": "במה אוכל לעזור? 😊", "items": []})
        
        if len(message) > 200:
            return jsonify({"message": "השאלה ארוכה מדי. תוכל לנסח אותה בקצרה?", "items": []})
        
        print(f"📩 Received message: {message}")
        
        if not is_pet_related_query(message):
            return jsonify({
                "message": "אני מתמחה רק במוצרים לחיות מחמד! 🐾 מה חיית המחמד שלך צריכה?",
                "items": []
            })
        
        detected_pet = get_pet_type_from_query(message)
        if detected_pet:
            print(f"🐾 Detected pet type: {detected_pet}")
        
        is_sku = is_sku_query(message)
        query_terms = expand_query_with_synonyms(message)
        rows = fetch_rows()
        items = []
        
        for r in rows:
            r = (r + [""] * 18)[:18]
            product_id = r[0]
            sku = r[3]
            name = r[4]
            short_desc = r[5]
            description = r[6]
            regular_price = r[7]
            sale_price = r[8]
            categories = r[9]
            brand = r[10]
            product_url = r[16]
            image_url = r[17]
            attr1 = r[11] if len(r) > 11 else ""
            attr2 = r[12] if len(r) > 12 else ""
            attr3 = r[13] if len(r) > 13 else ""
            attr4 = r[14] if len(r) > 14 else ""
            attr5 = r[15] if len(r) > 15 else ""
            
            if not name:
                continue
            
            if detected_pet and should_exclude_product(name, categories, detected_pet):
                continue
            
            if is_sku and sku:
                clean_sku = sku.replace(' ', '')
                clean_query = message.replace(' ', '').replace('מק"ט', '').replace('מקט', '')
                if clean_sku == clean_query or clean_query in clean_sku:
                    items.append({
                        "id": product_id, "name": name, "category": categories,
                        "price": sale_price if sale_price else regular_price,
                        "regular_price": regular_price, "sale_price": sale_price,
                        "description": short_desc or description, "image": image_url,
                        "brand": brand, "url": product_url, "sku": sku, "score": 1000,
                        "in_stock": True, "attributes": [attr1, attr2, attr3, attr4, attr5]
                    })
                    break
            
            price = sale_price if sale_price else regular_price
            try:
                price_f = float(str(price).replace(",", "").replace("₪", "").strip())
            except:
                price_f = None
            
            if filters:
                if "max_price" in filters and filters["max_price"] and price_f:
                    if price_f > float(filters["max_price"]):
                        continue
                if "min_price" in filters and filters["min_price"] and price_f:
                    if price_f < float(filters["min_price"]):
                        continue
            
            hay = " ".join([str(product_id), str(sku), str(name), str(short_desc), str(description), str(categories), str(brand)]).lower()
            matches = any(term in hay for term in query_terms)
            
            if matches or not message:
                product = {
                    "id": product_id, "name": name, "category": categories,
                    "price": price, "regular_price": regular_price, "sale_price": sale_price,
                    "description": short_desc or description, "image": image_url,
                    "brand": brand, "url": product_url, "sku": sku, "in_stock": True,
                    "attributes": [attr1, attr2, attr3, attr4, attr5]
                }
                score = calculate_product_score(product, query_terms, message)
                product["score"] = score
                items.append(product)
            
            if len(items) >= max(50, limit * 3):
                break
        
        items.sort(key=lambda x: x.get("score", 0), reverse=True)
        top_items = items[:limit]
        
        print(f"✅ Found {len(top_items)} products (from {len(items)} candidates)")
        
        if len(top_items) > 0:
            reply = get_llm_response(message, top_items)
        else:
            if openai_client:
                try:
                    fallback_prompt = """אתה שופיבוט של Shopipet - חנות מוצרים לחיות מחמד בלבד.
המשתמש חיפש אבל לא נמצאו מוצרים.
חשוב מאוד: זה חנות לכלבים, חתולים, ציפורים, דגים ומכרסמים - לא לבני אדם!
אם המשתמש שאל על "גור" - זה גור כלב או חתול, לא תינוק!
תן תשובה קצרה (1-2 משפטים) שמציעה לחפש בקטגוריות של חיות מחמד
היה חיובי וידידותי"""
                    fallback_messages = [
                        {"role": "system", "content": fallback_prompt},
                        {"role": "user", "content": f"חיפשתי: {message}"}
                    ]
                    completion = openai_client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=fallback_messages,
                        temperature=0.7,
                        max_tokens=100
                    )
                    reply = completion.choices[0].message.content
                except:
                    reply = "לא מצאתי בדיוק את זה. נסה לחפש 'מזון לגורים' או 'גור כלבים'! 🐾"
            else:
                reply = "לא מצאתי מוצרים מתאימים. נסה חיפוש אחר! 🔍"
        
        print("✅ Response sent successfully")
        
        return jsonify({"message": reply, "items": top_items})
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"message": "אופס! משהו השתבש. נסה שוב בעוד רגע 🔧", "error": str(e), "items": []}), 500

# --- Optional: make GET on /api/chat return a friendly message instead of 405 ---
@app.route('/api/chat', methods=['GET'])
def chat_get_info():
    return jsonify({"status": "ok",
                    "message": "Chat endpoint is alive. Use POST with {'message': '...'}"}), 200

# --- Static File Serving ---
#
# פונקציות להגשת קבצים סטטיים מהתיקיות
# 'web' (עבור ה-embed.js)
# 'public' (עבור openapi.json)
#
@app.route('/web/<path:filename>')
def serve_web_files(filename):
    """Serve JS and static assets under /web"""
    try:
        return send_from_directory(os.path.join(app.root_path, '..', 'web'), filename)
    except Exception as e:
        print(f"⚠️ Missing static file: {filename} ({e})")
        return jsonify({"error": f"File not found: {filename}"}), 404

@app.route('/public/<path:filename>')
def serve_public_files(filename):
    """Serve static files under /public"""
    try:
        return send_from_directory(os.path.join(app.root_path, '..', 'public'), filename)
    except Exception as e:
        print(f"⚠️ Missing public file: {filename} ({e})")
        return jsonify({"error": f"File not found: {filename}"}), 404

@app.route('/openapi.json')
def serve_openapi_file():
    """Serves the openapi.json file from the /public directory"""
    path = os.path.join(app.root_path, '..', 'public')
    return send_from_directory(path, 'openapi.json')

if __name__ == '__main__':
    app.run(debug=True)
