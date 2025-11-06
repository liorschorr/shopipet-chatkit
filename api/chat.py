from flask import Flask, jsonify, make_response
from openai import OpenAI
import gspread
import json
import os
import redis
import traceback
from google.oauth2.service_account import Credentials
from datetime import datetime
import threading
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
REDIS_INIT_ERROR = None
if KV_URL:
    try:
        redis_client = redis.Redis.from_url(KV_URL, decode_responses=True)
        redis_client.ping()
        print("✅ Redis client initialized successfully.")
    except Exception as e:
        print(f"❌ Redis initialization failed: {e}")
        REDIS_INIT_ERROR = str(e)
        redis_client = None


# === Hebrew → English column mapping ===
COLUMN_MAPPING = {
    "מזהה": "id",
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
    "IMAGE URL": "image_url"
}


def normalize_headers(headers):
    """Convert Hebrew column names to expected English keys"""
    normalized = []
    for h in headers:
        h = h.strip()
        normalized.append(COLUMN_MAPPING.get(h, h))
    return normalized


# === Long-running background job ===
def run_embedding_job():
    """Fetches catalog data, creates embeddings, and stores in Redis."""
    if not creds or not SPREADSHEET_ID or not SHEET_RANGE or not OPENAI_API_KEY:
        print("❌ JOB FAILED: Missing configuration variables.")
        return
    if not redis_client:
        print("❌ JOB FAILED: Redis client disconnected.")
        return

    try:
        SHEET_NAME = SHEET_RANGE.split('!')[0].strip()

        # 1. Fetch from Google Sheets
        client_gs = gspread.authorize(creds)
        sheet = client_gs.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
        rows = sheet.get_all_values()

        if not rows or len(rows) < 2:
            print("⚠️ No rows found in sheet.")
            return

        headers = normalize_headers(rows[0])
        data_rows = rows[1:]
        print(f"✅ Background job fetched {len(data_rows)} records.")

        # 2. Create Embeddings
        client_openai = OpenAI(api_key=OPENAI_API_KEY)
        products = []
        for r in data_rows:
            product = dict(zip(headers, r))
            if not product.get("name"):
                continue

            text = f"{product.get('name','')} {product.get('description','')} {product.get('category','')} {product.get('brand','')}"
            emb = client_openai.embeddings.create(
                model="text-embedding-3-small",
                input=text
            ).data[0].embedding

            products.append({"meta": product, "embedding": emb})

        # 3. Save to Redis
        products_json = json.dumps(products, ensure_ascii=False)
        redis_client.set('shopibot:smart_catalog_v1', products_json)

        size_in_bytes = len(products_json.encode('utf-8'))
        size_in_mb = size_in_bytes / (1024 * 1024)
        print(f"✅ JOB COMPLETE! Catalog size: {size_in_mb:.2f} MB, Total items: {len(products)}")

    except Exception as e:
        print(f"❌ CRITICAL JOB FAILURE: {e}")
        traceback.print_exc()


# === Main Route ===
@app.route("/api/update-catalog")
@app.route("/api/update-catalog/")
def update_catalog():
    if REDIS_INIT_ERROR:
        return jsonify({
            "status": "error",
            "message": f"Redis connection failed during startup. Error: {REDIS_INIT_ERROR}",
            "Debug": "Check KV_URL/shopipetbot_REDIS_URL value for correct password/host."
        }), 500

    if not creds or not redis_client or not OPENAI_API_KEY:
        return jsonify({
            "status": "error",
            "message": "Critical initialization failed. Check environment variables in Vercel settings.",
            "KV_URL_Status": "Connected" if redis_client else "Missing"
        }), 500

    thread = threading.Thread(target=run_embedding_job)
    thread.start()

    return make_response(jsonify({
        "status": "started",
        "message": "Update job started successfully in the background. Check /api/ping in 30 seconds to confirm the item count.",
        "storage_type": "Redis KV"
    }), 202)
