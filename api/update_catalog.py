from flask import Flask, jsonify
from openai import OpenAI
import gspread
import json
import os
import redis
import traceback
from google.oauth2.service_account import Credentials
from datetime import datetime
import sys
import urllib.parse
import time

app = Flask(__name__)

# === Configuration & Initialization (Global Scope) ===

# Sheets Config (using environment variables)
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")
SHEET_RANGE = os.environ.get("SHEET_RANGE")
GOOGLE_CREDENTIALS = os.environ.get("GOOGLE_CREDENTIALS")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Redis/KV Config
KV_URL = os.environ.get("KV_URL")

# Initialization Variables
creds = None
redis_client = None

# --- 1. Initialize Google Sheets Credentials ---
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

# --- 2. Initialize Redis Client ---
if KV_URL:
    try:
        # פתרון לחיבור ל-Redis/Vercel KV באמצעות URL
        url = urllib.parse.urlparse(KV_URL)
        redis_client = redis.Redis(
            host=url.hostname,
            port=url.port,
            password=url.password,
            username=url.username,
            ssl=True,
            db=0
        )
        redis_client.ping() 
        print("✅ Redis client initialized successfully.")
    except Exception as e:
        print(f"❌ Redis initialization failed: {e}")
        redis_client = None

# === Main Update Route ===

@app.route("/api/update-catalog")
@app.route("/api/update-catalog/")
def update_catalog():
    
    # --- בדיקות קריטיות לפני התחלה ---
    if not creds or not SPREADSHEET_ID or not SHEET_RANGE or not OPENAI_API_KEY:
         return jsonify({"status": "error", "message": "Missing Google Sheets/OpenAI configuration (Check all env vars).", "KV_URL_Status": "Connected" if redis_client else "Missing"}), 500
    if not redis_client:
        return jsonify({"status": "error", "message": "Missing or invalid Redis (KV_URL) configuration."}), 500
        
    # --- חילוץ שם הגיליון (התיקון) ---
    try:
        # בדיקת פורמט (למשל: Products!A2:R)
        if '!' not in SHEET_RANGE:
            raise ValueError(f"SHEET_RANGE must be in 'SheetName!A1:Z' format. Got: {SHEET_RANGE}")
            
        # התיקון הקריטי: חילוץ שם הגיליון וניקוי רווחים (.strip())
        SHEET_NAME = SHEET_RANGE.split('!')[0].strip() 
        
    except Exception as e:
        return jsonify({"status": "error", "message": f"SHEET_RANGE format error: {e}"}), 500

    # 1. Google Sheets Data Fetch
    try:
        print(f"Fetching data from Sheet Name: '{SHEET_NAME}'...")
        client_gs = gspread.authorize(creds)
        # הפקודה שמחפשת את הגיליון בשם הנקי
        sheet = client_gs.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME) 
        records = sheet.get_all_records()
        print(f"✅ Fetched {len(records)} records.")
    except Exception as e:
        traceback.print_exc()
        # אם השגיאה חוזרת, היא תהיה מפורטת יותר
        return jsonify({"status": "error", "message": f"Failed to fetch data from Google Sheets: {e}. Check sheet name and permissions."}), 500

    # 2. OpenAI Embedding Generation
    try:
        print("Generating OpenAI embeddings...")
        client_openai = OpenAI(api_key=OPENAI_API_KEY)
        products = []
        for r in records:
            text = f"{r.get('שם מוצר','')} {r.get('תיאור','')} {r.get('קטגוריה','')} {r.get('מותג','')}"
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
        # שמירה למפתח המשותף
        redis_client.set('shopibot:smart_catalog_v1', products_json)
        
        size_in_bytes = len(products_json.encode('utf-8'))
        size_in_mb = size_in_bytes / (1024 * 1024)
        print(f"✅ Catalog saved to 'shopibot:smart_catalog_v1' key. Size: {size_in_mb:.2f} MB.")
        
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
