from flask import Flask, jsonify, make_response
from openai import OpenAI
import gspread
import json
import os
import redis
import traceback
from google.oauth2.service_account import Credentials
from datetime import datetime
import threading # *** חדש: לריצה ברקע ***
import urllib.parse
import time

app = Flask(__name__)

# === Configuration & Initialization (Global Scope) ===
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")
SHEET_RANGE = os.environ.get("SHEET_RANGE")
GOOGLE_CREDENTIALS = os.environ.get("GOOGLE_CREDENTIALS")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
KV_URL = os.environ.get("shopipetbot_REDIS_URL") 

creds = None
redis_client = None

# ... (Initialization logic for Google and Redis remains the same) ...
if GOOGLE_CREDENTIALS:
    try:
        service_account_info = json.loads(GOOGLE_CREDENTIALS)
        creds = Credentials.from_service_account_info(
            service_account_info,
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        print("✅ Google Sheets credentials loaded.")
    except Exception as e:
        print(f"❌ Google credentials error during initialization: {e}")

if KV_URL:
    try:
        redis_client = redis.Redis.from_url(KV_URL, decode_responses=True)
        redis_client.ping() 
        print("✅ Redis client initialized successfully.")
    except Exception as e:
        print(f"❌ Redis initialization failed: {e}")
        redis_client = None

# === פונקציית העבודה הארוכה (Long-Running Task) ===
def run_embedding_job():
    """מבצע את כל העבודה הכבדה של יצירת הקטלוג ושמירתו."""
    
    # בדיקות קריטיות (יכולות לקרות שוב בתוך ה-thread)
    if not creds or not SPREADSHEET_ID or not SHEET_RANGE or not OPENAI_API_KEY:
        print("❌ JOB FAILED: Missing configuration variables.")
        return 
    if not redis_client:
        print("❌ JOB FAILED: Redis client disconnected.")
        return
        
    try:
        # חילוץ שם הגיליון (עם התיקון)
        SHEET_NAME = SHEET_RANGE.split('!')[0].strip() 
        
        # 1. Google Sheets Data Fetch
        client_gs = gspread.authorize(creds)
        sheet = client_gs.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME) 
        records = sheet.get_all_records()
        print(f"✅ Background job fetched {len(records)} records.")

        # 2. OpenAI Embedding Generation
        client_openai = OpenAI(api_key=OPENAI_API_KEY)
        products = []
        for r in records:
            text = f"{r.get('שם מוצר','')} {r.get('תיאור','')} {r.get('קטגוריה','')} {r.get('מותג','')}"
            emb = client_openai.embeddings.create(
                model="text-embedding-3-small",
                input=text
            ).data[0].embedding
            products.append({"meta": r, "embedding": emb})
        
        # 3. Save to Redis/KV Store
        products_json = json.dumps(products, ensure_ascii=False)
        redis_client.set('shopibot:smart_catalog_v1', products_json)
        
        size_in_bytes = len(products_json.encode('utf-8'))
        size_in_mb = size_in_bytes / (1024 * 1024)
        
        print(f"✅ JOB COMPLETE! Catalog size: {size_in_mb:.2f} MB.")

    except Exception as e:
        print(f"❌ CRITICAL JOB FAILURE: {e}")
        traceback.print_exc()

# === Main Update Route (Immediate Response) ===

@app.route("/api/update-catalog")
@app.route("/api/update-catalog/")
def update_catalog():
    
    # בדיקה אם האתחול הבסיסי נכשל
    if not creds or not redis_client or not OPENAI_API_KEY:
        return jsonify({"status": "error", "message": "Critical initialization failed. Check environment variables in Vercel settings.", "KV_URL_Status": "Connected" if redis_client else "Missing"}), 500
        
    # הפעלת המשימה בחוט נפרד (רק אם המשתנים תקינים)
    thread = threading.Thread(target=run_embedding_job)
    thread.start()

    # החזרת תשובה מיידית 202 ACCEPTED
    response = make_response(jsonify({
        "status": "started",
        "message": "Update job started successfully in the background. Check /api/ping in 30 seconds to confirm the item count.",
        "storage_type": "Redis KV"
    }), 202)
    
    return response

# ... (אם תרצה, הוסף את השורות של if __name__ == '__main__': כדי לאפשר הרצה מקומית, אבל הוא לא חיוני לפריסה ב-Vercel)
