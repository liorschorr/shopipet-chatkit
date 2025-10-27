from flask import Flask, jsonify
from openai import OpenAI
import gspread
import json
import os
import redis
import traceback
from google.oauth2.service_account import Credentials
from datetime import datetime

app = Flask(__name__)

# === Configuration & Initialization (Must be outside the function) ===

# Sheets Config (using environment variables)
# אם אתה משתמש ב-SHEET_NAME שאינו 'Sheet1', עדכן כאן
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")
SHEET_NAME = os.environ.get("SHEET_NAME", "Sheet1") 
GOOGLE_CREDENTIALS = os.environ.get("GOOGLE_CREDENTIALS")

# Redis/KV Config
KV_URL = os.environ.get("KV_URL")

# Initialize Google Sheets Credentials
creds = None
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

# Initialize Redis Client
redis_client = None
if KV_URL:
    try:
        # יוצר אובייקט Redis על בסיס מחרוזת החיבור
        redis_client = redis.Redis.from_url(KV_URL, decode_responses=True)
        redis_client.ping() # בדיקת חיבור
        print("✅ Redis client initialized successfully.")
    except Exception as e:
        print(f"❌ Redis initialization failed: {e}")
        redis_client = None


@app.route("/api/update-catalog")
def update_catalog():
    if not creds or not SPREADSHEET_ID:
         return jsonify({"status": "error", "message": "Missing Google Sheets configuration (SPREADSHEET_ID or GOOGLE_CREDENTIALS)."}), 500
    if not redis_client:
        return jsonify({"status": "error", "message": "Missing or invalid Redis (KV_URL) configuration."}), 500
        
    # 1. Google Sheets Data Fetch
    try:
        print(f"Fetching data from Sheet ID: {SPREADSHEET_ID} and Range: {SHEET_NAME}...")
        client_gs = gspread.authorize(creds)
        sheet = client_gs.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
        records = sheet.get_all_records()
        print(f"✅ Fetched {len(records)} records.")
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": f"Failed to fetch data from Google Sheets: {e}"}), 500

    # 2. OpenAI Embedding Generation
    try:
        print("Generating OpenAI embeddings...")
        client_openai = OpenAI()
        products = []
        for r in records:
            text = f"{r['שם מוצר']} {r.get('תיאור','')} {r.get('קטגוריה','')} {r.get('מותג','')}"
            emb = client_openai.embeddings.create(
                model="text-embedding-3-small",
                input=text
            ).data[0].embedding
            products.append({"meta": r, "embedding": emb})
        print(f"✅ Generated embeddings for {len(products)} products.")
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": f"Failed to generate embeddings: {e}. Check OPENAI_API_KEY."}), 500

    # 3. Save to Redis/KV Store
    try:
        print("Saving catalog to Redis...")
        products_json = json.dumps(products, ensure_ascii=False)
        # שמירה למפתח 'PRODUCT_CATALOG'
        redis_client.set('PRODUCT_CATALOG', products_json)
        
        size_in_bytes = len(products_json.encode('utf-8'))
        size_in_mb = size_in_bytes / (1024 * 1024)
        print(f"✅ Catalog saved to 'PRODUCT_CATALOG' key. Size: {size_in_mb:.2f} MB.")
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": f"Failed to save catalog to Redis: {e}"}), 500


    return jsonify({
        "status": "ok",
        "count": len(products),
        "storage_type": "Redis KV",
        "storage_size_MB": f"{size_in_mb:.2f}",
        "updated": datetime.now().isoformat()
    })
