from flask import Flask, jsonify
import os
import redis
import json
from datetime import datetime
from google.oauth2.service_account import Credentials
from openai import OpenAI

app = Flask(__name__)

# === קריאת משתני סביבה ===
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")
SHEET_RANGE = os.environ.get("SHEET_RANGE")
GOOGLE_CREDENTIALS = os.environ.get("GOOGLE_CREDENTIALS")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
KV_URL = os.environ.get("shopipetbot_REDIS_URL")

# === חיבורים ראשוניים ===
status = {
    "status": "ok",
    "message": "ShopiBot API is running ✅",
    "google_sheets": "disconnected",
    "openai": "disconnected",
    "storage": "disconnected",
    "smart_catalog_items": 0,
    "last_update": None
}

# --- בדיקת חיבור לגוגל ---
try:
    if GOOGLE_CREDENTIALS:
        service_account_info = json.loads(GOOGLE_CREDENTIALS)
        creds = Credentials.from_service_account_info(
            service_account_info,
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        status["google_sheets"] = "connected"
except Exception as e:
    status["google_sheets_error"] = str(e)

# --- בדיקת חיבור ל-OpenAI ---
try:
    if OPENAI_API_KEY:
        client = OpenAI(api_key=OPENAI_API_KEY)
        # קריאה קטנה לאימות
        _ = client.models.list()
        status["openai"] = "connected"
except Exception as e:
    status["openai_error"] = str(e)

# --- בדיקת Redis ---
try:
    if KV_URL:
        redis_client = redis.Redis.from_url(KV_URL, decode_responses=True)
        redis_client.ping()
        status["storage"] = "Vercel KV"
        # בדיקת כמות מוצרים
        data = redis_client.get('shopibot:smart_catalog_v1')
        if data:
            products = json.loads(data)
            status["smart_catalog_items"] = len(products)
            # בדוק אם שמרנו מתי עודכן
            last_update = redis_client.get('shopibot:last_update')
            if not last_update:
                last_update = datetime.utcnow().isoformat()
                redis_client.set('shopibot:last_update', last_update)
            status["last_update"] = last_update
except Exception as e:
    status["storage_error"] = str(e)

@app.route("/api/ping")
@app.route("/api/ping/")
def ping():
    return jsonify(status)
