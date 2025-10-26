from flask import Flask, jsonify
from openai import OpenAI
import gspread
import json
import os
from google.oauth2.service_account import Credentials
from datetime import datetime

app = Flask(__name__)

# --- התחלת קוד מתוקן ---

# 1. טעינת משתני סביבה
GOOGLE_CREDENTIALS_JSON = os.environ.get("GOOGLE_CREDENTIALS")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
SHEET_ID = os.environ.get("SPREADSHEET_ID", "1-XfEIXT0ovbhkWnBezc4v2xIcmUdONC7mAcep9554q8") # שימוש במזהה מה-README כברירת מחדל
SHEET_NAME = "Sheet1" # הנחה שזה שם הגיליון, שנה אם צריך
OUTPUT_PATH = "/tmp/catalog.json"  # שמירה זמנית ב־Vercel

# 2. הגדרת הרשאות בצורה נכונה (ממשתנה סביבה, לא מקובץ)
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
CREDS = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)

# 3. אתחול לקוחות (Clients)
client_gs = gspread.authorize(CREDS)
client_openai = OpenAI(api_key=OPENAI_API_KEY)

print(f"✅ update_catalog initialized. Sheet ID: {SHEET_ID}")

# --- סוף קוד מתוקן ---


@app.route("/api/update-catalog")
def update_catalog():
    try:
        print("Attempting to open Google Sheet...")
        sheet = client_gs.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
        records = sheet.get_all_records()
        print(f"✅ Fetched {len(records)} records from Google Sheets.")

        products = []
        for r in records:
            # ודא שהעמודות קיימות לפני שאתה משתמש בהן
            product_name = r.get('שם מוצר', '')
            description = r.get('תיאור', '')
            category = r.get('קטגוריה', '')
            brand = r.get('מותג', '')
            
            text = f"{product_name} {description} {category} {brand}"
            
            emb = client_openai.embeddings.create(
                model="text-embedding-3-small",
                input=text
            ).data[0].embedding
            
            # שמור את כל המטא-דאטה של המוצר
            products.append({"meta": r, "embedding": emb})

        print(f"✅ Generated {len(products)} embeddings.")

        with open(OUTPUT_PATH, "w", encoding="utf8") as f:
            json.dump(products, f, ensure_ascii=False, indent=2)

        print(f"✅ Smart Catalog saved to {OUTPUT_PATH}.")

        return jsonify({
            "status": "ok",
            "count": len(products),
            "updated": datetime.now().isoformat(),
            "sheet_id_used": SHEET_ID
        })
    except Exception as e:
        print(f"❌ ERROR in update_catalog: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

# הוספת נתיב שורש כדי שהפונקציה תגיב
@app.route("/api/update-catalog/")
def update_catalog_root():
    return update_catalog()
