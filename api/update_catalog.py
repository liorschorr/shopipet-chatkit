from flask import Flask, jsonify
from openai import OpenAI
import gspread
import json
import os
from google.oauth2.service_account import Credentials
from datetime import datetime
import sys
import traceback
from redis import Redis # חדש: יבוא Redis
import urllib.parse # חדש: לטיפול ב-URL

app = Flask(__name__)

def get_required_env(var_name):
    value = os.environ.get(var_name)
    if not value:
        print(f"❌ FATAL ERROR: Environment variable {var_name} is not set.")
        raise ValueError(f"Fatal Error: Environment variable {var_name} is not set.")
    return value

@app.route("/api/update-catalog")
@app.route("/api/update-catalog/")
def update_catalog():
    
    # --- 1. אתחול בתוך הפונקציה ---
    try:
        print("Initializing update_catalog function...")
        
        # --- טעינת משתני סביבה ---
        GOOGLE_CREDENTIALS_JSON = get_required_env("GOOGLE_CREDENTIALS")
        OPENAI_API_KEY = get_required_env("OPENAI_API_KEY")
        SHEET_ID = get_required_env("SPREADSHEET_ID")
        SHEET_RANGE = get_required_env("SHEET_RANGE") 
        KV_URL = get_required_env("KV_URL") # חדש: קבלת כתובת Vercel KV
        
        if '!' not in SHEET_RANGE:
            raise ValueError(f"Fatal Error: SHEET_RANGE must be in 'SheetName!A1:Z' format. Got: {SHEET_RANGE}")
            
        SHEET_NAME = SHEET_RANGE.split('!')[0]
        
        print(f"✅ Environment variables loaded. Target Sheet ID: {SHEET_ID}, Sheet Name: '{SHEET_NAME}'")

        # --- 2. אתחול Vercel KV ---
        print("Authenticating with Vercel KV...")
        url = urllib.parse.urlparse(KV_URL)
        client_kv = Redis(
            host=url.hostname,
            port=url.port,
            password=url.password,
            username=url.username,
            ssl=True,
            db=0 # ברירת מחדל
        )
        # בדיקת חיבור פשוטה
        client_kv.ping() 
        print("✅ Vercel KV client initialized and connected.")

        # --- 3. הגדרת הרשאות ---
        print("Authenticating with Google...")
        SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
        creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
        CREDS = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        print("✅ Google Credentials loaded.")

        # --- 4. אתחול לקוחות ---
        client_gs = gspread.authorize(CREDS)
        client_openai = OpenAI(api_key=OPENAI_API_KEY)
        print("✅ Google Sheets and OpenAI clients initialized.")

    except Exception as init_error:
        print(f"❌ CRITICAL INIT FAILED: {str(init_error)}")
        return jsonify({
            "status": "error",
            "error_type": "Initialization Failure",
            "message": str(init_error),
            "traceback": traceback.format_exc()
        }), 500

    # --- 5. לוגיקה ראשית (יצירת הקטלוג) ---
    try:
        print(f"Attempting to open Google Sheet: '{SHEET_NAME}'...")
        sheet = client_gs.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
        
        records = sheet.get_all_records()
        if not records:
            return jsonify({"status": "warning", "count": 0, "message": "No records found in sheet."})

        print(f"✅ Fetched {len(records)} records from Google Sheets.")
        
        products = []
        
        for i, r in enumerate(records):
            # ... (Embedding generation logic remains the same) ...
            # לוגיקת יצירת Embeddings:
            product_name = r.get('שם מוצר', '')
            description = r.get('תיאור', '')
            category = r.get('קטגוריה', '')
            brand = r.get('מותג', '')
            
            text_to_embed = f"שם: {product_name} | קטגוריה: {category} | מותג: {brand} | תיאור: {description}"
            text_to_embed = text_to_embed.replace("\n", " ").strip()

            if not text_to_embed or text_to_embed == "שם: | קטגוריה: | מותג: | תיאור:":
                continue

            emb = client_openai.embeddings.create(
                model="text-embedding-3-small",
                input=text_to_embed
            ).data[0].embedding
            
            products.append({"meta": r, "embedding": emb})

        print(f"✅ Generated {len(products)} embeddings.")
        
        # --- 6. שמירת הקטלוג ב-Vercel KV ---
        print(f"Attempting to save {len(products)} items to Vercel KV...")
        
        # המרת הנתונים למחרוזת JSON כדי לשמור ב-Redis
        json_data = json.dumps(products, ensure_ascii=False) 
        
        # שמירת הקטלוג באמצעות מפתח משותף
        client_kv.set("shopibot:smart_catalog_v1", json_data) 

        print(f"✅ Smart Catalog (JSON string, {len(json_data):,} bytes) saved to Vercel KV.")

        return jsonify({
            "status": "ok",
            "count": len(products),
            "updated": datetime.now().isoformat(),
            "sheet_id_used": SHEET_ID,
            "sheet_name_used": SHEET_NAME,
            "storage_used": "Vercel KV" # אישור שהשימוש הוא ב-KV
        })
        
    except Exception as runtime_error:
        print(f"❌ ERROR in update_catalog runtime: {str(runtime_error)}")
        return jsonify({
            "status": "error",
            "error_type": "Runtime Failure",
            "message": str(runtime_error),
            "traceback": traceback.format_exc()
        }), 500
