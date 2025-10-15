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
SHEET_RANGE = os.environ.get("SHEET_RANGE", "Sheet1!A2:F")
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
if OPENAI_AVAILABLE and OPENAI_API_KEY:
    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        print("✅ OpenAI initialized")
    except Exception as e:
        print(f"❌ OpenAI error: {e}")

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
        return []

def get_llm_response(message, products):
    """Get response from OpenAI"""
    if not openai_client:
        return "אני כאן לעזור! (OpenAI לא מחובר כרגע)"
    
    try:
        system_prompt = (
            "You are ShopiBot, a helpful Hebrew-speaking assistant for a pet supply store. "
            "Answer clearly and concisely in Hebrew. Reference recommended products when relevant. "
            "Prices are in ILS (₪). Keep tone warm and friendly."
        )
        
        products_for_llm = [
            {"id": p["id"], "name": p["name"], "category": p["category"], 
             "price": p["price"], "description": p["description"]}
            for p in products[:5]  # Top 5 only
        ]
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message},
            {"role": "system", "content": "Available products: " + json.dumps(products_for_llm, ensure_ascii=False)}
        ]
        
        completion = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.4,
            max_tokens=300
        )
        
        return completion.choices[0].message.content if completion.choices else "אני כאן לעזור!"
        
    except Exception as e:
        print(f"❌ OpenAI error: {e}")
        return f"סליחה, יש לי בעיה זמנית. ({str(e)[:50]})"

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
            # Pad row to ensure 6 columns
            r = (r + [""] * 6)[:6]
            pid, name, category, price, desc, img = r
            
            if not name:  # Skip empty rows
                continue
            
            # Parse price
            try:
                price_f = float(str(price).replace(",", "").replace("₪", "").strip())
            except:
                price_f = None
            
            # Apply filters
            ok = True
            if filters:
                if "category" in filters and filters["category"]:
                    if str(category).lower().strip() != str(filters["category"]).lower().strip():
                        ok = False
                if "max_price" in filters and filters["max_price"] and price_f:
                    if price_f > float(filters["max_price"]):
                        ok = False
            
            if not ok:
                continue
            
            # Text matching score
            ql = message.lower()
            hay = " ".join([pid, name, category, str(price), desc]).lower()
            score = 1
            if ql and ql in hay:
                score += 2
            
            items.append({
                "id": pid,
                "name": name,
                "category": category,
                "price": price,
                "description": desc,
                "image": img,
                "score": score
            })
            
            # Limit results
            if len(items) >= max(20, limit * 2):
                break
        
        # Sort by relevance
        items.sort(key=lambda x: x.get("score", 0), reverse=True)
        top_items = items[:limit]
        
        print(f"✅ Found {len(top_items)} products")
        
        # Get LLM response
        reply = get_llm_response(message, top_items)
        
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
app = app
