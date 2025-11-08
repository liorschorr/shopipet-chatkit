# שמור קובץ זה בשם: api/chat.py
# (הקובץ היחיד בתיקיית api)

from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
import json
import os
import re
import numpy as np
from numpy.linalg import norm
from googleapiclient.discovery import build
from google.oauth2 import service_account
from openai import OpenAI
import traceback
import sys
from redis import Redis
import urllib.parse
import time

# --- 1. הגדרות ואתחול ---

# === Create Flask app ===
# זוהי נקודת הכניסה הראשית ש-Vercel יריץ
app = Flask(__name__)
CORS(app)

# === Configuration ===
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")
SHEET_RANGE = os.environ.get("SHEET_RANGE", "Sheet1!A2:R") # הטווח *ללא* כותרות
GOOGLE_CREDENTIALS = os.environ.get("GOOGLE_CREDENTIALS")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
KV_URL = os.environ.get("shopipetbot_REDIS_URL")

# Initialize clients
creds = None
openai_client = None
product_catalog_embeddings = []
kv_client = None

# Initialize Google Sheets
if GOOGLE_CREDENTIALS:
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
if OPENAI_API_KEY:
    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        print("✅ OpenAI initialized")
    except Exception as e:
        print(f"❌ OpenAI error: {e}")

# Initialize Vercel KV (Redis)
if KV_URL:
    try:
        kv_client = Redis.from_url(KV_URL, decode_responses=True)
        kv_client.ping()
        print("✅ Vercel KV client initialized.")
    except Exception as e:
        print(f"❌ Vercel KV connection error: {e}")
        kv_client = None


# --- 2. לוגיקת הטעינה מ-KV ---
def load_smart_catalog():
    """טוען את קטלוג ה-Embeddings מ-Vercel KV"""
    global product_catalog_embeddings
    
    if not kv_client:
        print("⚠️ Vercel KV client not connected. Cannot load smart catalog.")
        return False
        
    try:
        print("Attempting to load Smart Catalog from Vercel KV...")
        
        json_data = kv_client.get("shopibot:smart_catalog_v1")
        
        if json_data:
            data = json.loads(json_data)
            
            product_catalog_embeddings = []
            for item in data:
                if "meta" in item and "embedding" in item:
                    # ודא שה-embedding הוא מערך numpy לחישובים
                    item["embedding_np"] = np.array(item["embedding"])
                    product_catalog_embeddings.append(item)
                    
            if product_catalog_embeddings:
                print(f"✅ Smart Catalog loaded successfully from KV with {len(product_catalog_embeddings)} items.")
                return True
                
    except Exception as e:
        print(f"❌ Error loading Smart Catalog from KV: {e}")
    
    print("⚠️ Smart Catalog not found in KV or empty. Falling back to text search.")
    product_catalog_embeddings = []
    return False

# טעינה ראשונית בעת עליית השרת (Cold Start)
load_smart_catalog()


# --- 3. חיפוש חכם (Embedded Search) ---
def get_embedding(text, model="text-embedding-3-small"):
   text = text.replace("\n", " ")
   if not text or text.isspace():
       print("⚠️ get_embedding: קיבל טקסט ריק, מחזיר None")
       return None
   return openai_client.embeddings.create(input = [text], model=model).data[0].embedding

def find_products_by_embedding(query, limit=5):
    """מחפש מוצרים באמצעות השוואת Embeddings (חיפוש חכם)"""
    if not openai_client:
        raise Exception("OpenAI client not available")
    if not product_catalog_embeddings:
        # נסיון טעינה נוסף אם הקטלוג ריק (למקרה של Cold Start כושל)
        print("Smart catalog empty, attempting reload...")
        if not load_smart_catalog():
             raise Exception("Smart Catalog not loaded and reload failed")

    query_embedding = np.array(get_embedding(query))
    
    results = []
    for item in product_catalog_embeddings:
        sim = np.dot(query_embedding, item["embedding_np"]) / (norm(query_embedding) * norm(item["embedding_np"]))
        results.append({"product": item["meta"], "score": sim})
    
    # מיון לפי הציון הגבוה ביותר
    results.sort(key=lambda x: x["score"], reverse=True)
    
    # פורמט פלט
    top_products = []
    for res in results[:limit]:
        p = res["product"]
        top_products.append({
            "id": p.get("id"),
            "name": p.get("name"),
            "category": p.get("category"),
            "price": p.get("sale_price") if p.get("sale_price") else p.get("regular_price"),
            "regular_price": p.get("regular_price"),
            "sale_price": p.get("sale_price"),
            "description": p.get("short_description") or p.get("description"),
            "image": p.get("image_url"),
            "brand": p.get("brand"),
            "url": p.get("url"),
            "sku": p.get("sku"),
            "score": res["score"],
            "in_stock": True # הנחה שמה שבקטלוג קיים במלאי
        })
    return top_products


# --- 4. לוגיקת חיפוש הגיבוי הטקסטואלי (והגדרות) ---

# כאן יוכנסו ההגדרות שלך:
# SYNONYMS = { ... }
# PET_EXCLUSIONS = { ... }

# === מיפוי עמודות (משני הקבצים) ===
COLUMN_MAPPING = {
    "מזהה": "id",
    "מזהה ייחודי": "id",
    "מוצר": "name",
    "שם מוצר": "name",
    "שם": "name",
    "מק\"ט": "sku",
    "קטגוריה": "category",
    "קטגוריות": "category",
    "מותג": "brand",
    "תיאור": "description",
    "תיאור קצר": "short_description",
    "מחיר רגיל": "regular_price",
    "מחיר מבצע": "sale_price",
    "קישור": "url",
    "כתובת תמונה": "image_url",
    "תמונה": "image_url",
    "URL": "url",
    "IMAGE URL": "image_url",
    "סטטוס": "status",
    "מלאי": "stock",
    "תכונה 1": "attr1",
    "תכונה 2": "attr2",
    "תכונה 3": "attr3",
    "תכונה 4": "attr4",
    "תכונה 5": "attr5",
}

def normalize_headers(headers):
    """Convert Hebrew column names to expected English keys"""
    normalized = []
    for h in headers:
        h_clean = h.strip()
        # השתמש במפה, ואם לא קיים, השתמש בשם הנקי
        normalized.append(COLUMN_MAPPING.get(h_clean, h_clean))
    return normalized

# --- פונקציות עזר לחיפוש טקסט ---
# (יש להעתיק לכאן את הפונקציות שלך: get_pet_type_from_query, is_pet_related_query, וכו')
def is_pet_related_query(query):
    # ... (הטמע את הפונקציה שלך כאן) ...
    return True # החלף בלוגיקה האמיתית

def fetch_rows():
    """ פונקציית הגיבוי הקיימת (מביאה נתונים מ-A2:R) """
    if not creds:
        print("⚠️ No credentials for Google Sheets (Fallback)")
        return []
    try:
        service = build("sheets", "v4", credentials=creds)
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=SHEET_RANGE).execute()
        rows = result.get("values", [])
        print(f"✅ Fetched {len(rows)} rows from Google Sheets (Fallback)")
        return rows
    except Exception as e:
        print(f"❌ Error fetching rows: {e}")
        traceback.print_exc()
        return []

def find_products_by_text_fallback(message, limit=5, filters={}):
    """ מבצע חיפוש טקסטואלי פשוט כגיבוי (החיפוש ה"טיפש") """
    print("⚡️ Running Text-Based Fallback Search")
    rows = fetch_rows() # משתמש ב-fetch_rows שמביא מ-A2
    items = []
    
    # מיפוי כותרות קשיח עבור ה-Fallback (מכיוון ש-A2:R לא כולל כותרות)
    # **חשוב**: התאם את זה לסדר העמודות האמיתי שלך מ-A עד R
    headers_fallback = [
        "id", "status", "stock", "sku", "name", "short_description", "description",
        "regular_price", "sale_price", "category", "brand", 
        "attr1", "attr2", "attr3", "attr4", "attr5", "url", "image_url"
    ]

    for r in rows:
        r_padded = (r + [""] * len(headers_fallback))[:len(headers_fallback)]
        product = dict(zip(headers_fallback, r_padded))

        if not product.get("name"):
            continue

        # ... (כאן תהיה שאר לוגיקת החיפוש הטקסטואלי שלך - התאמת מילים, ניקוד וכו') ...
        
        # לוגיקת התאמה פשוטה לדוגמה:
        hay = " ".join([str(product.get(k, '')) for k in headers_fallback]).lower()
        if message.lower() in hay:
             items.append(product)

    # כאן צריך להיות מיון לפי ניקוד (Score)
    return items[:limit]


def get_llm_response(message, products, context=None):
    """ הפונקציה שלך ליצירת תגובת שפה טבעית """
    # ... (הטמע את הפונקציה שלך כאן) ...
    if products:
        return "מצאתי כמה מוצרים שתואמים לחיפוש שלך! 🐾"
    else:
        return "לא מצאתי מוצרים שתואמים בדיוק. נסה לחפש משהו אחר?"

# --- 5. לוגיקת עדכון קטלוג (חדש - מ-update_catalog.py) ---
def create_and_store_embeddings():
    """
    מביא נתונים מ-Sheets, יוצר Embeddings ושומר ל-Vercel KV.
    זוהי פונקציה סינכרונית וארוכה.
    """
    if not creds:
        return {"status": "error", "message": "Google Sheets not connected."}
    if not openai_client:
        return {"status": "error", "message": "OpenAI not connected."}
    if not kv_client:
        return {"status": "error", "message": "Vercel KV not connected."}

    try:
        print("--- 🚀 Starting Catalog Update Job ---")
        
        service = build("sheets", "v4", credentials=creds)
        sheet_service = service.spreadsheets()
        
        # קביעת שם הגיליון מתוך הטווח
        sheet_name = SHEET_RANGE.split('!')[0].strip("'")
        
        # 1א. הבאת כותרות (שורה 1)
        header_range = f"'{sheet_name}'!1:1"
        header_result = sheet_service.values().get(spreadsheetId=SPREADSHEET_ID, range=header_range).execute()
        header_rows = header_result.get("values", [])
        
        if not header_rows:
            return {"status": "error", "message": "Sheet is empty or headers not found in row 1."}
            
        headers = normalize_headers(header_rows[0])
        print(f"✅ Fetched headers: {headers}")

        # 1ב. הבאת נתונים (מ-A2:R)
        data_result = sheet_service.values().get(spreadsheetId=SPREADSHEET_ID, range=SHEET_RANGE).execute()
        data_rows = data_result.get("values", [])
        print(f"✅ Fetched {len(data_rows)} data rows.")

        # 2. יצירת Embeddings
        products = []
        for i, r in enumerate(data_rows):
            # התאמת אורך השורה לכותרות
            r_padded = (r + [""] * len(headers))[:len(headers)]
            product = dict(zip(headers, r_padded))
            
            if not product.get("name"):
                continue # דילוג על שורות ללא שם מוצר

            text_to_embed = (
                f"{product.get('name','')} "
                f"{product.get('brand','')} "
                f"{product.get('category','')} "
                f"{product.get('description','')} "
                f"{product.get('short_description','')}"
            ).strip()

            if len(text_to_embed) < 10:
                print(f"⚠️ Skipping item (not enough text): {product.get('name')}")
                continue

            try:
                emb = get_embedding(text_to_embed)
                if emb:
                    # שמור את המטא-דאטה ואת ה-Embedding
                    products.append({"meta": product, "embedding": emb})
                
                if (i + 1) % 50 == 0:
                    print(f"... Generated {i + 1} embeddings ...")
                    
            except Exception as e:
                print(f"❌ Error embedding item {product.get('name')}: {e}")
                time.sleep(1) # המתנה קצרה במקרה של Rate Limit

        print(f"✅ Generated {len(products)} embeddings successfully.")

        # 3. שמירה ל-Redis (Vercel KV)
        if not products:
             return {"status": "warning", "message": "No products were generated. KV not updated."}

        products_json = json.dumps(products, ensure_ascii=False)
        kv_client.set('shopibot:smart_catalog_v1', products_json)
        
        size_in_mb = len(products_json.encode('utf-8')) / (1024 * 1024)
        print(f"✅ JOB COMPLETE! Saved {len(products)} items to KV. (Size: {size_in_mb:.2f} MB)")

        # 4. טעינה מחדש של הקטלוג לזיכרון
        load_smart_catalog()
        
        return {
            "status": "success",
            "message": f"Catalog updated: {len(products)} items stored.",
            "items_count": len(products),
            "size_mb": round(size_in_mb, 2)
        }

    except Exception as e:
        error_info = traceback.format_exc()
        print(f"❌ CRITICAL JOB FAILURE: {e}\n{error_info}")
        return {"status": "error", "message": f"Fatal update error: {str(e)}", "traceback": error_info}


# --- 6. ROUTES (הלב של האפליקציה) ---

@app.route('/', methods=['GET'])
@app.route('/api', methods=['GET'])
def health_check():
    """בדיקת בריאות כללית"""
    return jsonify({
        "status": "ok",
        "message": "ShopiBot API is running ✅ (Unified App)",
        "google_sheets": "connected" if creds else "disconnected",
        "openai": "connected" if openai_client else "disconnected",
        "smart_catalog_items": len(product_catalog_embeddings),
        "storage": "Vercel KV" if kv_client else "Disconnected"
    })

@app.route('/api/ping', methods=['GET'])
def ping_check():
    """נתיב Ping ששימש לבדיקות (זהה ל-health_check)"""
    # נסיון לטעון מחדש את הקטלוג אם הוא ריק
    if not product_catalog_embeddings:
        load_smart_catalog()
        
    return jsonify({
        "status": "ok",
        "message": "ShopiBot API Ping ✅",
        "smart_catalog_items": len(product_catalog_embeddings),
        "storage": "Vercel KV" if kv_client else "Disconnected"
    })

@app.route('/api/test-sheets', methods=['GET'])
def test_sheets():
    """בדיקה מהירה של החיבור לגוגל שיטס"""
    rows = fetch_rows()
    return jsonify({"status": "ok", "rows_count": len(rows)})


# --- ה-ROUTE החדש לעדכון הקטלוג ---
@app.route('/api/update-catalog', methods=['GET', 'POST'])
def handle_update_catalog():
    """
    מפעיל את תהליך העדכון הסינכרוני.
    זה ירוץ עד שהתהליך יסתיים או עד Timeout של Vercel.
    """
    print("--- 🚀 API CALL: Starting Synchronous Catalog Update ---")
    
    result = create_and_store_embeddings()
    status_code = 200 if result['status'] == 'success' else 500
    
    print(f"--- 🏁 Catalog Update Finished with status: {result['status']} ---")
    return jsonify(result), status_code

# ---
# נתיב הצ'אט הראשי
# ---

@app.route('/api/chat', methods=['POST', 'OPTIONS'])
def chat():
    """הנתיב הראשי של הצ'אטבוט"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        req_body = request.get_json() or {}
        message = req_body.get("message", "").strip()
        filters = req_body.get("filters", {})
        
        if not message:
            return jsonify({"message": "במה אוכל לעזור? 😊", "items": []})
        
        if not is_pet_related_query(message):
             return jsonify({
                 "message": "אני מתמחה רק במוצרים לחיות מחמד! 🐾 מה חיית המחמד שלך צריכה?",
                 "items": []
             })

        top_items = []
        search_mode = "smart"
        
        try:
            # נסיון 1: חיפוש חכם
            top_items = find_products_by_embedding(message, limit=5)
            print(f"✅ Smart Search found {len(top_items)} products.")
            if not top_items:
                raise Exception("Smart search found 0 results, trying fallback.")

        except Exception as e:
            # גיבוי: חיפוש טקסטואלי
            print(f"⚠️ Smart Search failed ({e}). Falling back to text search.")
            search_mode = "fallback_text"
            top_items = find_products_by_text_fallback(message, limit=5, filters=filters)
            print(f"✅ Text Fallback Search found {len(top_items)} products.")
            
        # קבלת תגובת שפה טבעית
        reply = get_llm_response(message, top_items)
        
        return jsonify({"message": reply, "items": top_items, "search_mode": search_mode})
        
    except Exception as e:
        print(f"❌ ERROR in /api/chat: {str(e)}")
        traceback.print_exc()
        return jsonify({"message": "אופס! משהו השתבש. נסה שוב בעוד רגע 🔧", "error": str(e), "items": []}), 500

@app.route('/api/chat', methods=['GET'])
def chat_get_info():
    """מונע שגיאת 405 אם ניגשים ל-chat ב-GET"""
    return jsonify({"status": "ok",
                    "message": "Chat endpoint is alive. Use POST with {'message': '...'}"}), 200

# --- Static File Serving (אם צריך) ---
@app.route('/web/<path:filename>')
def serve_web_files(filename):
    return send_from_directory(os.path.join(app.root_path, '..', 'web'), filename)

@app.route('/public/<path:filename>')
def serve_public_files(filename):
    return send_from_directory(os.path.join(app.root_path, '..', 'public'), filename)

@app.route('/openapi.json')
def serve_openapi_file():
    return send_from_directory(os.path.join(app.root_path, '..', 'public'), 'openapi.json')
@app.route('/api/clear-kv', methods=['GET', 'POST'])
def clear_kv():
    """מנקה את כל המפתחות מ-Vercel KV"""
    if not kv_client:
        return jsonify({"status": "error", "message": "KV not connected"})
    
    try:
        # מחק את הקטלוג הישן
        kv_client.delete('shopibot:smart_catalog_v1')
        
        # אפשר גם למחוק מפתחות נוספים אם יש
        # kv_client.flushdb()  # ⚠️ זה ימחק הכל!
        
        return jsonify({
            "status": "success",
            "message": "KV cleared successfully"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
