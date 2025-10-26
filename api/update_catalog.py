from flask import Flask, jsonify
from openai import OpenAI
import gspread
import json
import os
from google.oauth2.service_account import Credentials
from datetime import datetime
import sys

app = Flask(__name__)

# --- פונקציות עזר לבדיקת תקינות ---
def get_required_env(var_name):
    """
    טוען משתנה סביבה הכרחי.
    זורק שגיאה ברורה אם הוא חסר.
    """
    value = os.environ.get(var_name)
    if not value:
        print(f"❌ FATAL ERROR: Environment variable {var_name} is not set.")
        # שימוש ב-sys.exit גורם לקריסה מבוקרת עם הודעה ברורה בלוג
        sys.exit(f"Error: Missing required environment variable {var_name}")
    return value

try:
    # --- 1. טעינת משתני סביבה ובדיקתם ---
    print("Initializing update_catalog function...")
    GOOGLE_CREDENTIALS_JSON = get_required_env("GOOGLE_CREDENTIALS")
    OPENAI_API_KEY = get_required_env("OPENAI_API_KEY")
    SHEET_ID = get_required_env("SPREADSHEET_ID")
    SHEET_RANGE = get_required_env("SHEET_RANGE") # למשל: "Products!A2:R"
    
    # --- 2. חילוץ שם הגיליון מתוך ה-RANGE ---
    if '!' not in SHEET_RANGE:
        print(f"❌ FATAL ERROR: SHEET_RANGE must be in 'SheetName!A1:Z' format. Got: {SHEET_RANGE}")
        sys.exit("Error: Invalid SHEET_RANGE format.")
        
    SHEET_NAME = SHEET_RANGE.split('!')[0]
    OUTPUT_PATH = "/tmp/catalog.json"
    
    print(f"✅ Environment variables loaded. Target Sheet ID: {SHEET_ID}, Sheet Name: '{SHEET_NAME}'")

    # --- 3. הגדרת הרשאות (מתוך try...except) ---
    print("Authenticating with Google...")
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
    CREDS = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    print("✅ Google Credentials loaded.")

    # --- 4. אתחול לקוחות (Clients) ---
    client_gs = gspread.authorize(CREDS)
    client_openai = OpenAI(api_key=OPENAI_API_KEY)
    print("✅ Google Sheets and OpenAI clients initialized.")

except Exception as e:
    # תופס שגיאות אתחול קריטיות
    print(f"❌ CRITICAL INIT FAILED: {str(e)}")
    import traceback
    traceback.print_exc()
    # אם האתחול נכשל, אין טעם להמשיך
    sys.exit("Failed during initialization")


# --- 5. הגדרת ה-Route הראשי ---
@app.route("/api/update-catalog")
def update_catalog():
    try:
        print(f"Attempting to open Google Sheet: '{SHEET_NAME}'...")
        sheet = client_gs.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
        
        # שימוש ב- get_all_records() דורש שהשורה הראשונה תהיה כותרות
        records = sheet.get_all_records()
        if not records:
            print("⚠️ Warning: No records found in sheet. Check SHEET_NAME and permissions.")
            return jsonify({"status": "warning", "count": 0, "message": "No records found in sheet."})

        print(f"✅ Fetched {len(records)} records from Google Sheets.")
        
        products = []
        
        # --- 6. יצירת Embeddings ---
        for i, r in enumerate(records):
            # ודא שהעמודות קיימות לפני שאתה משתמש בהן
            product_name = r.get('שם מוצר', '')
            description = r.get('תיאור', '')
            category = r.get('קטגוריה', '')
            brand = r.get('מותג', '')
            
            # טקסט נקי ליצירת ה-Embedding
            text_to_embed = f"שם: {product_name} | קטגוריה: {category} | מותג: {brand} | תיאור: {description}"
            text_to_embed = text_to_embed.replace("\n", " ").strip()

            if not text_to_embed or text_to_embed == "שם: | קטגוריה: | מותג: | תיאור:":
                print(f"⚠️ Skipping row {i+2}: Product has no data.")
                continue

            emb = client_openai.embeddings.create(
                model="text-embedding-3-small",
                input=text_to_embed
            ).data[0].embedding
            
            # שמור את כל המטא-דאטה של המוצר
            products.append({"meta": r, "embedding": emb})

        print(f"✅ Generated {len(products)} embeddings.")
        
        # --- 7. שמירת הקטלוג החכם ---
        with open(OUTPUT_PATH, "w", encoding="utf8") as f:
            json.dump(products, f, ensure_ascii=False, indent=2)

        print(f"✅ Smart Catalog saved to {OUTPUT_PATH}.")

        return jsonify({
            "status": "ok",
            "count": len(products),
            "updated": datetime.now().isoformat(),
            "sheet_id_used": SHEET_ID,
            "sheet_name_used": SHEET_NAME
        })
        
    except Exception as e:
        # זוהי הלכידה שתופסת שגיאות *בזמן ריצה*
        print(f"❌ ERROR in update_catalog runtime: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # החזרת שגיאת 500 עם פירוט
        return jsonify({
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

# הוספת נתיב שורש כדי שהפונקציה תגיב
@app.route("/api/update-catalog/")
def update_catalog_root():
    return update_catalog()
