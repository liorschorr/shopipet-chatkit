from flask import Flask, request, jsonify
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
    # Pet names
    'כלב': ['כלבים', 'דוג', 'דוגי', 'כלבלב', 'puppy', 'dog', 'dogs'],
    'חתול': ['חתולים', 'קיטי', 'חתולון', 'חתלתול', 'cat', 'kitten', 'cats'],
    'גור': ['גורים', 'גור כלבים', 'גור חתולים', 'puppies', 'kittens'],
    'ציפור': ['ציפורים', 'bird', 'birds'],
    'דג': ['דגים', 'fish'],
    
    # Product types
    'מזון': ['אוכל', 'מזונות', 'אוכלים', 'מאכל', 'food', 'אוכלן', 'buy', 'pay', 'purchase', 'acquire'],
    'יבש': ['מזון יבש', 'קיבל', 'dry', 'דראי', 'יבשים'],
    'רטוב': ['מזון רטוב', 'שימורים', 'פחית', 'wet', 'וואט', 'רטובים'],
    'חטיף': ['חטיפים', 'פינוק', 'פינוקים', 'treats', 'snacks', 'נשנושים'],
    'צעצוע': ['צעצועים', 'משחק', 'משחקים', 'toy', 'toys'],
    'חול': ['ליטר', 'חולות', 'litter', 'sand', 'box', 'housing', 'unit', 'package'],
    
    # Brands
    'מונג': ['מונג׳', 'monge', 'mong', 'מונז', 'מונז׳'],
    'פרופלאן': ['proplan', 'פרו פלאן', 'פרו פלן', 'pro plan', 'pro-plan'],
    'ג׳וסרה': ['גוסרה', 'josera', 'גוזרה', 'ג׳וזרה', 'josra'],
    'הריטג': ['הריטג׳', 'heritage', 'הריטז', 'הריטז׳', 'recipe'],
    'אקאנה': ['אקנה', 'acana', 'akana'],
    
    # Ingredients
    'סלמון': ['salmon', 'salomon', 'סלומון'],
    
    # Special attributes
    'סנסיטיב': ['סנסטיב', 'sensitive', 'רגיש'],
    'מטאבוליק': ['metabolic', 'מטבוליק', 'מתבוליק'],
    
    # Sizes
    'גדול': ['גדולים', 'לארג', 'large', 'big', 'ענק'],
    'קטן': ['קטנים', 'סמול', 'small', 'mini', 'מיני', 'זעיר'],
    'בינוני': ['בינוניים', 'medium', 'מדיום'],
    
    # Life stages
    'גור': ['גורים', 'צעיר', 'junior', 'puppy', 'kitten', 'צעירים'],
    'בוגר': ['בוגרים', 'adult', 'אדולט'],
    'מבוגר': ['סניור', 'זקן', 'senior', 'aged', 'מבוגרים'],
}

# CRITICAL: Exclusion rules - if searching for one pet, REJECT products with other pets
PET_EXCLUSIONS = {
    'כלב': ['חתול', 'חתולים', 'cat', 'cats', 'kitten', 'קיטי', 'חתלתול'],
    'חתול': ['כלב', 'כלבים', 'dog', 'dogs', 'puppy', 'דוג', 'כלבלב'],
    'ציפור': ['כלב', 'חתול', 'dog', 'cat', 'כלבים', 'חתולים'],
    'דג': ['כלב', 'חתול', 'dog', 'cat', 'כלבים', 'חתולים'],
}

def get_pet_type_from_query(query):
    """Detect which pet type the user is asking about"""
    query_lower = query.lower()
    
    for pet, synonyms in SYNONYMS.items():
        if pet in ['כלב', 'חתול', 'ציפור', 'דג', 'גור']:
            all_terms = [pet] + synonyms
            if any(term in query_lower for term in all_terms):
                return pet
    return None

def should_exclude_product(product_name, product_category, detected_pet):
    """
    STRICT RULE: If searching for dogs, NO cat words allowed in name/category.
    If searching for cats, NO dog words allowed in name/category.
    """
    if not detected_pet or detected_pet not in PET_EXCLUSIONS:
        return False
    
    text_to_check = f"{product_name} {product_category}".lower()
    exclusion_words = PET_EXCLUSIONS[detected_pet]
    
    # If ANY exclusion word appears in name or category - REJECT!
    for word in exclusion_words:
        if word in text_to_check:
            print(f"⚠️ EXCLUDED: '{product_name}' contains '{word}' (searching for {detected_pet})")
            return True
    
    return False

def expand_query_with_synonyms(query):
    """Expand query with synonyms for better matching"""
    expanded = [query.lower()]
    words = query.lower().split()
    
    for word in words:
        for key, synonyms in SYNONYMS.items():
            if word in synonyms or word == key:
                expanded.extend([key] + synonyms)
    
    return list(set(expanded))

def is_sku_query(query):
    """Check if query is a SKU search"""
    clean = query.replace(' ', '').replace('מק"ט', '').replace('מקט', '')
    return len(clean) > 5 and sum(c.isdigit() for c in clean) > len(clean) * 0.7

def calculate_product_score(product, query_terms, original_query):
    """Calculate relevance score for ranking"""
    score = 0
    name = product.get('name', '').lower()
    category = product.get('category', '').lower()
    brand = product.get('brand', '').lower()
    desc = product.get('description', '').lower()
    
    # Exact match in name (50 points)
    if original_query.lower() in name:
        score += 50
    
    # Partial matches (35 points)
    name_matches = sum(1 for term in query_terms if term in name)
    score += min(name_matches * 10, 35)
    
    # Category match (25 points)
    cat_matches = sum(1 for term in query_terms if term in category)
    score += min(cat_matches * 8, 25)
    
    # Brand match (15 points)
    if any(term in brand for term in query_terms):
        score += 15
    
    # Description match (10 points)
    desc_matches = sum(1 for term in query_terms if term in desc)
    score += min(desc_matches * 2, 10)
    
    # Availability bonus (25 points)
    if product.get('in_stock', False):
        score += 25
    else:
        score += 5
    
    # Sale bonus (15 points)
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
    """Fetch products from Google Sheet"""
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
    """Get response from OpenAI with ShopiBot personality"""
    if not openai_client:
        return "הנה כמה מוצרים שמצאתי עבורך! 🐾"
    
    try:
        system_prompt = """אתה שופיבוט (ShopiBot) - עוזר קניות AI מקצועי של Shopipet.co.il.

חוקים קריטיים:
1. דבר רק בעברית טבעית וחמה
2. תשובות קצרות: 1-2 משפטים בלבד (מקסימום 120 תווים)
3. אל תפרט מוצרים - הם יוצגו בכרטיסים
4. אל תכלול לינקים או מחירים - הם בכרטיסים
5. היה טבעי - אל תגיד "בדקתי במאגר" או "לאחר בדיקה"

דוגמאות לתשובות טובות:
✅ "מצאתי כמה אפשרויות מעולות! תסתכל על המוצרים למטה 🐕"
✅ "יש לי המלצות נהדרות בשבילך! 😊"
✅ "הנה בדיוק מה שחיפשת! 🎯"

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

@app.route('/', methods=['GET'])
@app.route('/api', methods=['GET'])
@app.route('/api/ping', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "message": "ShopiBot API is running ✅",
        "google_sheets": "connected" if creds else "disconnected",
        "openai": "connected" if openai_client else "disconnected"
    })

@app.route('/api/test-sheets', methods=['GET'])
def test_sheets():
    """Test Google Sheets connection"""
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
    """Handle chat requests with ShopiBot intelligence"""
    
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        req_body = request.get_json() or {}
        message = req_body.get("message", "").strip()
        limit = req_body.get("limit", 5)
        filters = req_body.get("filters", {})
        
        if not message:
            return jsonify({
                "message": "במה אוכל לעזור? 😊",
                "items": []
            })
        
        if len(message) > 200:
            return jsonify({
                "message": "השאלה ארוכה מדי. תוכל לנסח אותה בקצרה?",
                "items": []
            })
        
        print(f"📩 Received message: {message}")
        
        # Detect pet type from query
        detected_pet = get_pet_type_from_query(message)
        if detected_pet:
            print(f"🐾 Detected pet type: {detected_pet}")
        
        # Check if SKU search
        is_sku = is_sku_query(message)
        
        # Expand query with synonyms
        query_terms = expand_query_with_synonyms(message)
        
        # Fetch products from Google Sheet
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
            
            # Attributes (L-P)
            attr1 = r[11] if len(r) > 11 else ""
            attr2 = r[12] if len(r) > 12 else ""
            attr3 = r[13] if len(r) > 13 else ""
            attr4 = r[14] if len(r) > 14 else ""
            attr5 = r[15] if len(r) > 15 else ""
            
            if not name:
                continue
            
            # CRITICAL EXCLUSION: If searching for dogs, reject cats (and vice versa)
            if detected_pet and should_exclude_product(name, categories, detected_pet):
                continue  # Skip this product entirely!
            
            # SKU exact match
            if is_sku and sku:
                clean_sku = sku.replace(' ', '')
                clean_query = message.replace(' ', '').replace('מק"ט', '').replace('מקט', '')
                if clean_sku == clean_query or clean_query in clean_sku:
                    items.append({
                        "id": product_id,
                        "name": name,
                        "category": categories,
                        "price": sale_price if sale_price else regular_price,
                        "regular_price": regular_price,
                        "sale_price": sale_price,
                        "description": short_desc or description,
                        "image": image_url,
                        "brand": brand,
                        "url": product_url,
                        "sku": sku,
                        "score": 1000,
                        "in_stock": True,
                        "attributes": [attr1, attr2, attr3, attr4, attr5]
                    })
                    break
            
            # Price filtering
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
            
            # Text matching with expanded terms
            hay = " ".join([
                str(product_id), str(sku), str(name), str(short_desc),
                str(description), str(categories), str(brand)
            ]).lower()
            
            matches = any(term in hay for term in query_terms)
            
            if matches or not message:
                product = {
                    "id": product_id,
                    "name": name,
                    "category": categories,
                    "price": price,
                    "regular_price": regular_price,
                    "sale_price": sale_price,
                    "description": short_desc or description,
                    "image": image_url,
                    "brand": brand,
                    "url": product_url,
                    "sku": sku,
                    "in_stock": True,
                    "attributes": [attr1, attr2, attr3, attr4, attr5]
                }
                
                score = calculate_product_score(product, query_terms, message)
                product["score"] = score
                
                items.append(product)
            
            if len(items) >= max(50, limit * 3):
                break
        
        # Sort by score
        items.sort(key=lambda x: x.get("score", 0), reverse=True)
        top_items = items[:limit]
        
        print(f"✅ Found {len(top_items)} products (from {len(items)} candidates)")
        
        # Get LLM response
        if len(top_items) > 0:
            reply = get_llm_response(message, top_items)
        else:
            if openai_client:
                try:
                    fallback_prompt = """אתה שופיבוט. המשתמש חיפש אבל לא נמצאו מוצרים.
תן תשובה קצרה (1-2 משפטים) שמציעה לנסות חיפוש אחר או קטגוריות.
היה חיובי וידידותי. אל תתנצל יותר מדי."""
                    
                    fallback_messages = [
                        {"role": "system", "content": fallback_prompt},
                        {"role": "user", "content": f"חיפשתי: {message}"}
                    ]
                    completion = openai_client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=fallback_messages,
                        temperature=0.7,
                        max_tokens=80
                    )
                    reply = completion.choices[0].message.content
                except:
                    reply = "לא מצאתי בדיוק את זה, אבל נסה לחפש במילים אחרות! 🔍"
            else:
                reply = "לא מצאתי מוצרים מתאימים. נסה חיפוש אחר! 🔍"
        
        print("✅ Response sent successfully")
        
        return jsonify({
            "message": reply,
            "items": top_items
        })
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            "message": "אופס! משהו השתבש. נסה שוב בעוד רגע 🔧",
            "error": str(e),
            "items": []
        }), 500

if __name__ == '__main__':
    app.run(debug=True)
from flask import send_from_directory
import os

@app.route("/openapi.json")
def serve_openapi():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    public_dir = os.path.join(current_dir, "..", "public")
    return send_from_directory(public_dir, "openapi.json")
