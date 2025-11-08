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


# --- 2. לוגיקת הטעינה מ-KV (מתוקנת!) ---
def load_smart_catalog():
    """טוען את קטלוג ה-Embeddings מ-Vercel KV - עם טיפול משופר בשגיאות"""
    global product_catalog_embeddings
    
    # אתחול ברירת מחדל
    product_catalog_embeddings = []
    
    if not kv_client:
        print("⚠️ Vercel KV client not connected. Cannot load smart catalog.")
        return False
        
    try:
        print("Attempting to load Smart Catalog from Vercel KV...")
        
        json_data = kv_client.get("shopibot:smart_catalog_v1")
        
        if not json_data:
            print("⚠️ No data found in KV for key 'shopibot:smart_catalog_v1'")
            return False
            
        data = json.loads(json_data)
        
        if not isinstance(data, list):
            print("⚠️ Invalid data format in KV (expected list)")
            return False
        
        loaded_items = []
        for item in data:
            try:
                if "meta" in item and "embedding" in item:
                    # ודא שה-embedding הוא מערך numpy לחישובים
                    item["embedding_np"] = np.array(item["embedding"], dtype=np.float32)
                    loaded_items.append(item)
            except Exception as e:
                print(f"⚠️ Error processing item in catalog: {e}")
                continue
                
        if loaded_items:
            product_catalog_embeddings = loaded_items
            print(f"✅ Smart Catalog loaded successfully from KV with {len(product_catalog_embeddings)} items.")
            return True
        else:
            print("⚠️ No valid items found in KV data")
            return False
                
    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error loading Smart Catalog from KV: {e}")
        traceback.print_exc()
    except Exception as e:
        print(f"❌ Error loading Smart Catalog from KV: {e}")
        traceback.print_exc()
    
    print("⚠️ Smart Catalog load failed. Falling back to text search.")
    return False

# טעינה ראשונית בעת עליית השרת (Cold Start)
# זה לא יקרס את השרת אפילו אם נכשל
try:
    load_smart_catalog()
except Exception as e:
    print(f"⚠️ Initial catalog load failed (non-critical): {e}")


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

    query_embedding = np.array(get_embedding(query), dtype=np.float32)
    
    results = []
    for item in product_catalog_embeddings:
        sim = np.dot(query_embedding, item["embedding_np"]) / (norm(query_embedding) * norm(item["embedding_np"]))
        results.append({"product": item["meta"], "score": float(sim)})
    
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
def is_pet_related_query(query):
    """
    בודק אם השאלה קשורה לחיות מחמד או לשירות החנות.
    אם לא - OpenAI ידאג לתת תשובה מנומסת.
    """
    # מילות מפתח ברורות שמצביעות על שאלה לא רלוונטית
    irrelevant_keywords = [
        'מתכון', 'בישול', 'אוכל אנושי', 'מכונית', 'בית', 'נדל"ן',
        'פוליטיקה', 'כדורגל', 'מוזיקה', 'סרט', 'משחק מחשב'
    ]
    
    query_lower = query.lower()
    
    # אם יש מילה ברורה שזה לא קשור - החזר False
    for keyword in irrelevant_keywords:
        if keyword in query_lower:
            return False
    
    # אחרת - תן ל-OpenAI לטפל בזה (הוא יותר חכם)
    return True

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
    rows = fetch_rows()
    items = []
    # הוסף את הלוגיקה שלך לחיפוש טקסטואלי
    return items

def get_llm_response(message, products, context=None):
    """
    יוצר תגובה בשפה טבעית באמצעות OpenAI
    מבוסס רק על המוצרים שנמצאו בDB
    """
    if not openai_client:
        # גיבוי אם OpenAI לא זמין
        if products:
            return f"מצאתי {len(products)} מוצרים מתאימים עבורך! 🐾"
        else:
            return "לא מצאתי מוצרים מתאימים. נסה לנסח את החיפוש אחרת!"
    
    try:
        # בניית רשימת המוצרים למודל
        if products:
            products_summary = "\n".join([
                f"- {p['name']} ({p.get('brand', 'ללא מותג')}) - ₪{p.get('price', 'N/A')}"
                for p in products[:5]  # מקסימום 5 מוצרים
            ])
            products_context = f"מצאתי את המוצרים הבאים:\n{products_summary}"
        else:
            products_context = "לא נמצאו מוצרים מתאימים בחנות."
        
        # System prompt - הוראות ברורות למודל
        system_prompt = """אתה שופיבוט - עוזר וירטואלי של חנות שופיפט למוצרי חיות מחמד.

כללים חשובים:
1. ענה רק על שאלות הקשורות לחיות מחמד, מוצרי חיות מחמד, או שירות החנות
2. אל תציע לעולם מוצרים שלא מופיעים ברשימת המוצרים שקיבלת
3. אם שאלו שאלה לא קשורה לחיות מחמד - הסבר שאתה מתמחה רק במוצרים לחיות מחמד
4. תן תשובות קצרות (1-2 משפטים), ידידותיות ומועילות
5. השתמש באימוג'י רלוונטי (🐶🐱🐹🐦🐠) בצורה מתונה
6. אם יש מוצרים - תאר אותם בקצרה ובצורה מזמינה
7. אם אין מוצרים - הצע לנסות חיפוש אחר או לפנות לשירות לקוחות

דוגמאות לתשובות טובות:
- "מצאתי 3 מזונות איכותיים לגורים! המומלץ ביותר הוא Royal Canin - מזון פרימיום המותאם במיוחד לגורי כלבים 🐶"
- "יש לי 5 משחקים מעולים לחתולים! מגוון של משחקי טיזר, כדורים ומתקני גירוד 🐱"
- "לא מצאתי בדיוק מה שחיפשת, אבל תוכל לפנות לשירות הלקוחות שלנו בטלפון או לנסות חיפוש אחר"

אל תכתוב משפטים כמו "לפי הנתונים שקיבלתי" או "במאגר שלי" - דבר בצורה טבעית."""

        # User prompt
        user_prompt = f"""שאלת הלקוח: "{message}"

{products_context}

תן תשובה קצרה וידידותית (עד 2 משפטים) שמתאימה לשאלה ולמוצרים שנמצאו."""

        # קריאה ל-OpenAI
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",  # מודל חסכוני וטוב
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=150,
            temperature=0.7
        )
        
        reply = response.choices[0].message.content.strip()
        return reply
        
    except Exception as e:
        print(f"⚠️ Error in get_llm_response: {e}")
        traceback.print_exc()
        
        # תשובת גיבוי במקרה של שגיאה
        if products:
            return f"מצאתי {len(products)} מוצרים עבורך! 🐾"
        else:
            return "לא מצאתי מוצרים מתאימים. אשמח לעזור בחיפוש אחר!"


# --- 5. לוגיקת עדכון קטלוג (משופרת וממוטבת!) ---
def create_and_store_embeddings():
    """
    מביא נתונים מ-Sheets, יוצר Embeddings ושומר ל-Vercel KV.
    גרסה ממוטבת עם דחיסה וצמצום metadata.
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

        # 2. יצירת Embeddings עם אופטימיזציה
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
                    # 🔥 דחיסה: שמור כ-float32 במקום float64 (חוסך 50%)
                    emb_compressed = np.array(emb, dtype=np.float32).tolist()
                    
                    # 🔥 צמצום metadata: שמור רק שדות חיוניים (חוסך עוד 30-50%)
                    minimal_meta = {
                        "id": product.get("id", ""),
                        "name": product.get("name", ""),
                        "category": product.get("category", ""),
                        "brand": product.get("brand", ""),
                        "regular_price": product.get("regular_price", ""),
                        "sale_price": product.get("sale_price", ""),
                        "short_description": product.get("short_description", "")[:200],  # הגבל ל-200 תווים
                        "image_url": product.get("image_url", ""),
                        "url": product.get("url", ""),
                        "sku": product.get("sku", "")
                    }
                    
                    products.append({"meta": minimal_meta, "embedding": emb_compressed})
                
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
        size_in_mb = len(products_json.encode('utf-8')) / (1024 * 1024)
        
        print(f"📦 Catalog size: {size_in_mb:.2f} MB")
        
        # בדיקת גודל לפני שמירה
        if size_in_mb > 25:
            print(f"⚠️ WARNING: Catalog is very large ({size_in_mb:.2f} MB). May cause Redis memory issues.")
        
        kv_client.set('shopibot:smart_catalog_v1', products_json)
        
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


# --- ה-ROUTE לניקוי KV (חדש!) ---
@app.route('/api/clear-kv', methods=['GET', 'POST'])
def clear_kv():
    """מנקה את הקטלוג מ-Vercel KV"""
    if not kv_client:
        return jsonify({"status": "error", "message": "KV not connected"})
    
    try:
        # מחק את הקטלוג הישן
        deleted = kv_client.delete('shopibot:smart_catalog_v1')
        
        # נקה גם את הקטלוג בזיכרון
        global product_catalog_embeddings
        product_catalog_embeddings = []
        
        return jsonify({
            "status": "success",
            "message": f"KV cleared successfully. Keys deleted: {deleted}"
        })
    except Exception as e:
        return jsonify({
            "status": "error", 
            "message": str(e),
            "traceback": traceback.format_exc()
        })


@app.route('/api/flush-kv', methods=['GET', 'POST'])
def flush_kv():
    """⚠️ מנקה את כל ה-KV לגמרי (שימוש רק במצבי חירום!)"""
    if not kv_client:
        return jsonify({"status": "error", "message": "KV not connected"})
    
    try:
        # מחק הכל!
        kv_client.flushdb()
        
        # נקה גם את הקטלוג בזיכרון
        global product_catalog_embeddings
        product_catalog_embeddings = []
        
        return jsonify({
            "status": "success",
            "message": "⚠️ All KV data has been flushed completely!"
        })
    except Exception as e:
        return jsonify({
            "status": "error", 
            "message": str(e),
            "traceback": traceback.format_exc()
        })


@app.route('/api/kv-info', methods=['GET'])
def kv_info():
    """מציג מידע על שימוש ב-KV"""
    if not kv_client:
        return jsonify({"status": "error", "message": "KV not connected"})
    
    try:
        info = kv_client.info('memory')
        keys = kv_client.keys('*')
        
        return jsonify({
            "status": "ok",
            "used_memory": info.get('used_memory_human', 'N/A'),
            "used_memory_peak": info.get('used_memory_peak_human', 'N/A'),
            "maxmemory": info.get('maxmemory_human', 'N/A'),
            "total_keys": len(keys),
            "keys": keys[:20]  # רק 20 הראשונים
        })
    except Exception as e:
        return jsonify({
            "status": "error", 
            "message": str(e),
            "traceback": traceback.format_exc()
        })


# --- ה-ROUTE לעדכון הקטלוג ---
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


# --- נתיב הצ'אט הראשי ---
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
        
        # בדיקה בסיסית בלבד - OpenAI יטפל בשאלות לא רלוונטיות בצורה חכמה יותר
        # (הפונקציה is_pet_related_query מזהה רק שאלות ברורות שלא קשורות)

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


# --- Static File Serving ---
@app.route('/web/<path:filename>')
def serve_web_files(filename):
    return send_from_directory(os.path.join(app.root_path, '..', 'web'), filename)

@app.route('/public/<path:filename>')
def serve_public_files(filename):
    return send_from_directory(os.path.join(app.root_path, '..', 'public'), filename)

@app.route('/openapi.json')
def serve_openapi_file():
    return send_from_directory(os.path.join(app.root_path, '..', 'public'), 'openapi.json')
