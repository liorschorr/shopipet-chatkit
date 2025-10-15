from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os

# Import Google Sheets - with error handling
try:
    from googleapiclient.discovery import build
    from google.oauth2 import service_account
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    print("Warning: Google API not available")

# Import OpenAI - with error handling
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("Warning: OpenAI not available")

# === Create Flask app ===
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# === Configuration ===
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "1-XfEIXT0ovbhkWnBezc4v2xIcmUdONC7mAcep9554q8")
SHEET_RANGE = os.environ.get("SHEET_RANGE", "Sheet1!A2:R")  # 18 columns: A-R
GOOGLE_CREDENTIALS = os.environ.get("GOOGLE_CREDENTIALS")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Initialize clients
creds = None
openai_client = None

# Try to initialize Google Sheets
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

# Try to initialize OpenAI
print(f"🔍 Debug: OPENAI_AVAILABLE = {OPENAI_AVAILABLE}")
print(f"🔍 Debug: OPENAI_API_KEY exists = {bool(OPENAI_API_KEY)}")
print(f"🔍 Debug: OPENAI_API_KEY length = {len(OPENAI_API_KEY) if OPENAI_API_KEY else 0}")
print(f"🔍 Debug: OPENAI_API_KEY starts with = {OPENAI_API_KEY[:7] if OPENAI_API_KEY else 'None'}...")

if OPENAI_AVAILABLE and OPENAI_API_KEY:
    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        print("✅ OpenAI initialized successfully")
    except Exception as e:
        print(f"❌ OpenAI initialization error: {e}")
        import traceback
        traceback.print_exc()
else:
    if not OPENAI_AVAILABLE:
        print("❌ OpenAI library not available")
    if not OPENAI_API_KEY:
        print("❌ OPENAI_API_KEY not set in environment")


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


def get_llm_response(message, products):
    """Get response from OpenAI"""
    if not openai_client:
        return "אני כאן לעזור!"
    
    try:
        system_prompt = (
            "You are ShopiBot, a friendly Hebrew-speaking assistant for ShopiPet, a pet supply store. "
            "Your role is to provide a brief, warm introduction to the products that will be displayed below your message. "
            "\n\nIMPORTANT RULES:"
            "\n- Write ONLY in Hebrew"
            "\n- Keep response under 2-3 sentences (max 150 characters)"
            "\n- Be warm and conversational"
            "\n- DO NOT list products - they will be shown automatically as cards"
            "\n- DO NOT include links or prices - they are in the product cards"
            "\n- Just give a brief helpful intro or recommendation"
            "\n\nExamples of GOOD responses:"
            "\n- 'מצאתי כמה אפשרויות מעולות עבור הכלב שלך! תסתכל על המוצרים מטה 🐕'"
            "\n- 'יש לי המלצות נהדרות בשבילך! בחרתי את המוצרים הכי מתאימים 😊'"
            "\n- 'הנה כמה מוצרים איכותיים שמתאימים בדיוק למה שחיפשת! 🎯'"
        )
        
        # Only send product names for context, not full details
        product_context = ", ".join([p["name"][:30] for p in products[:3]])
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message},
            {"role": "system", "content": f"Products available (for context only): {product_context}"}
        ]
        
        completion = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=100  # Limit response length
        )
        
        return completion.choices[0].message.content if completion.choices else "הנה כמה אפשרויות נהדרות! 🐾"
        
    except Exception as e:
        print(f"❌ OpenAI error: {e}")
        import traceback
        traceback.print_exc()
        return "הנה כמה מוצרים שמצאתי עבורך! 🐾"


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
        
        # Parse first row to show structure
        sample = None
        if rows:
            r = (rows[0] + [""] * 18)[:18]
            sample = {
                "מזהה": r[0], 
                "שם": r[4], 
                "קטגוריות": r[9],
                "מחיר_רגיל": r[7], 
                "מחיר_מבצע": r[8], 
                "מותג": r[10], 
                "תמונה": r[17]
            }
        
        return jsonify({
            "status": "ok",
            "rows_count": len(rows),
            "sample_product": sample,
            "credentials_present": bool(GOOGLE_CREDENTIALS),
            "creds_initialized": bool(creds),
            "spreadsheet_id": SPREADSHEET_ID,
            "sheet_range": SHEET_RANGE
        })
    except Exception as e:
        import traceback
        return jsonify({
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "credentials_present": bool(GOOGLE_CREDENTIALS),
            "creds_initialized": bool(creds)
        }), 500


@app.route('/api/chat', methods=['POST', 'OPTIONS'])
def chat():
    """Handle chat requests"""
    
    # Handle preflight
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        # Parse request
        req_body = request.get_json() or {}
        message = req_body.get("message", "")
        limit = req_body.get("limit", 5)
        filters = req_body.get("filters", {})
        
        print(f"📩 Received message: {message}")
        
        # Fetch products from Google Sheet
        rows = fetch_rows()
        items = []
        
        for r in rows:
            # Pad row to ensure 18 columns (A-R)
            r = (r + [""] * 18)[:18]
            
            # Map columns according to structure:
            # A=מזהה, B=מזהה אב, C=סוג, D=מק"ט, E=שם, F=תיאור קצר, 
            # G=תיאור, H=מחיר רגיל, I=מחיר מבצע, J=קטגוריות, K=מותג,
            # L-P=תכונות 1-5, Q=URL, R=IMAGE URL
            
            product_id = r[0]       # מזהה (A)
            parent_id = r[1]        # מזהה אב (B)
            product_type = r[2]     # סוג (C)
            sku = r[3]              # מק"ט (D)
            name = r[4]             # שם (E)
            short_desc = r[5]       # תיאור קצר (F)
            description = r[6]      # תיאור (G)
            regular_price = r[7]    # מחיר רגיל (H)
            sale_price = r[8]       # מחיר מבצע (I)
            categories = r[9]       # קטגוריות (J)
            brand = r[10]           # מותג (K)
            attr1 = r[11]           # תכונה 1 (L)
            attr2 = r[12]           # תכונה 2 (M)
            attr3 = r[13]           # תכונה 3 (N)
            attr4 = r[14]           # תכונה 4 (O)
            attr5 = r[15]           # תכונה 5 (P)
            product_url = r[16]     # URL (Q)
            image_url = r[17]       # IMAGE URL (R)
            
            if not name:  # Skip empty rows
                continue
            
            # Use sale price if available, otherwise regular price
            price = sale_price if sale_price else regular_price
            
            # Parse price for filtering
            try:
                price_str = str(price).replace(",", "").replace("₪", "").strip()
                price_f = float(price_str) if price_str else None
            except:
                price_f = None
            
            # Apply filters
            ok = True
            if filters:
                if "category" in filters and filters["category"]:
                    cat_filter = str(filters["category"]).lower().strip()
                    cat_product = str(categories).lower().strip()
                    if cat_filter not in cat_product and cat_product not in cat_filter:
                        ok = False
                
                if "max_price" in filters and filters["max_price"] and price_f:
                    if price_f > float(filters["max_price"]):
                        ok = False
                
                if "brand" in filters and filters["brand"]:
                    brand_filter = str(filters["brand"]).lower().strip()
                    brand_product = str(brand).lower().strip()
                    if brand_filter not in brand_product and brand_product not in brand_filter:
                        ok = False
            
            if not ok:
                continue
            
            # Text matching score
            ql = message.lower()
            hay = " ".join([
                str(product_id), str(sku), str(name), str(short_desc), 
                str(description), str(categories), str(brand),
                str(attr1), str(attr2), str(attr3), str(attr4), str(attr5)
            ]).lower()
            
            score = 1
            if ql:
                # Count how many query words appear in the product text
                query_words = ql.split()
                matches = sum(1 for word in query_words if word in hay)
                score += matches * 2
            
            # Combine description (prefer short description)
            full_desc = short_desc if short_desc else description
            
            items.append({
                "id": product_id,
                "name": name,
                "category": categories,
                "price": price,
                "description": full_desc,
                "image": image_url,
                "brand": brand,
                "url": product_url,
                "sku": sku,
                "score": score
            })
            
            # Limit results during processing
            if len(items) >= max(50, limit * 3):
                break
        
        # Sort by relevance score
        items.sort(key=lambda x: x.get("score", 0), reverse=True)
        top_items = items[:limit]
        
        print(f"✅ Found {len(top_items)} products (from {len(items)} candidates)")
        
        # Get LLM response
        if len(top_items) > 0:
            reply = get_llm_response(message, top_items)
        else:
            # No products found - give helpful response
            if openai_client:
                try:
                    fallback_messages = [
                        {"role": "system", "content": "You are ShopiBot for ShopiPet. User searched but no products found. Give a brief, helpful suggestion in Hebrew (2 sentences max). Suggest trying different search terms or categories."},
                        {"role": "user", "content": message}
                    ]
                    completion = openai_client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=fallback_messages,
                        temperature=0.7,
                        max_tokens=100
                    )
                    reply = completion.choices[0].message.content
                except:
                    reply = "מצטער, לא מצאתי מוצרים מתאימים לחיפוש שלך. נסה לחפש במילים אחרות או בקטגוריות שונות! 🔍"
            else:
                reply = "מצטער, לא מצאתי מוצרים מתאימים. נסה לחפש במילים אחרות! 🔍"
        
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
            "message": "שגיאה בשרת. אנא נסה שוב מאוחר יותר.",
            "error": str(e),
            "items": []
        }), 500


# Vercel needs this
if __name__ == '__main__':
    app.run(debug=True)
