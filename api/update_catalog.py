from flask import Flask, jsonify
from openai import OpenAI
import gspread
import json
import os
from google.oauth2.service_account import Credentials
from datetime import datetime
import sys
import traceback

app = Flask(__name__)

def get_required_env(var_name):
    """
    טוען משתנה סביבה הכרחי.
    זורק שגיאת ValueError אם הוא חסר, כדי שנוכל לתפוס אותה.
    """
    value = os.environ.get(var_name)
    if not value:
        print(f"❌ FATAL ERROR: Environment variable {var_name} is not set.")
        raise ValueError(f"Fatal Error: Environment variable {var_name} is not set.")
    return value

@app.route("/api/update-catalog")
@app.route("/api/update-catalog/")
def update_catalog():
    
    # --- 1. אתחול בתוך הפונקציה ---
    # אנחנו מבצעים את כל האתחול כאן, בתוך בלוק try...except
    # כדי שנוכל להחזיר שגיאת JSON ברורה במקום לקרוס.
    try:
        print("Initializing update_catalog function...")
        
        # --- 1. טעינת משתני סביבה ובדיקתם ---
        GOOGLE_CREDENTIALS_JSON = get_required_env("GOOGLE_CREDENTIALS")
        OPENAI_API_KEY = get_required_env("OPENAI_API_KEY")
        SHEET_ID = get_required_env("SPREADSHEET_ID")
        SHEET_RANGE = get_required_env("SHEET_RANGE") # למשל: "Products!A2:R"
        
        # --- 2. חילוץ שם הגיליון מתוך ה-RANGE ---
        if '!' not in SHEET_RANGE:
            raise ValueError(f"Fatal Error: SHEET_RANGE must be in 'SheetName!A1:Z' format. Got: {SHEET_RANGE}")
            
        SHEET_NAME = SHEET_RANGE.split('!')[0]
        OUTPUT_PATH = "/tmp/catalog.json"
        
        print(f"✅ Environment variables loaded. Target Sheet ID: {SHEET_ID}, Sheet Name: '{SHEET_NAME}'")

        # --- 3. הגדרת הרשאות (זה התיקון המרכזי) ---
        print("Authenticating with Google...")
        SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
        # קורא את ההגדרות מהטקסט שהעתקת (משתנה סביבה)
        creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
        # משתמש ב-from_service_account_info במקום from_service_account_file
        CREDS = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        print("✅ Google Credentials loaded.")

        # --- 4. אתחול לקוחות (Clients) ---
        client_gs = gspread.authorize(CREDS)
        client_openai = OpenAI(api_key=OPENAI_API_KEY)
        print("✅ Google Sheets and OpenAI clients initialized.")

    except Exception as init_error:
        # --- זה הקטע החשוב ---
        # במקום לקרוס, אנחנו מחזירים את השגיאה בדפדפן
        print(f"❌ CRITICAL INIT FAILED: {str(init_error)}")
        return jsonify({
            "status": "error",
            "error_type": "Initialization Failure",
            "message": str(init_error),
            "traceback": traceback.format_exc()
        }), 500

    # --- 5. לוגיקה ראשית (רק אם האתחול הצליח) ---
    try:
        print(f"Attempting to open Google Sheet: '{SHEET_NAME}'...")
        sheet = client_gs.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
        
        records = sheet.get_all_records()
        if not records:
            print("⚠️ Warning: No records found in sheet. Check SHEET_NAME and permissions.")
            return jsonify({"status": "warning", "count": 0, "message": "No records found in sheet."})

        print(f"✅ Fetched {len(records)} records from Google Sheets.")
        
        products = []
        
        # --- 6. יצירת Embeddings ---
        for i, r in enumerate(records):
            product_name = r.get('שם מוצר', '')
            description = r.get('תיאור', '')
            category = r.get('קטגוריה', '')
            brand = r.get('מותג', '')
            
            text_to_embed = f"שם: {product_name} | קטגוריה: {category} | מותג: {brand} | תיאור: {description}"
            text_to_embed = text_to_embed.replace("\n", " ").strip()

            if not text_to_embed or text_to_embed == "שם: | קטגוריה: | מותג: | תיאור:":
                print(f"⚠️ Skipping row {i+2}: Product has no data.")
                continue

            emb = client_openai.embeddings.create(
                model="text-embedding-3-small",
                input=text_to_embed
            ).data[0].embedding
            
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
        
    except Exception as runtime_error:
        # תופס שגיאות בזמן הריצה של הלוגיקה
        print(f"❌ ERROR in update_catalog runtime: {str(runtime_error)}")
        return jsonify({
            "status": "error",
            "error_type": "Runtime Failure",
            "message": str(runtime_error),
            "traceback": traceback.format_exc()
        }), 500
