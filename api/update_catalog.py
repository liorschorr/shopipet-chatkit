from flask import Flask, jsonify
from openai import OpenAI
import gspread
import json
from google.oauth2.service_account import Credentials
from datetime import datetime

app = Flask(__name__)

# קובץ ההרשאה לשיטס כבר מחובר בפרויקט שלך
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
CREDS = Credentials.from_service_account_file("service_account.json", scopes=SCOPES)

SHEET_ID = "YOUR_SHEET_ID"
SHEET_NAME = "Sheet1"
OUTPUT_PATH = "/tmp/catalog.json"  # שמירה זמנית ב־Vercel

@app.route("/api/update-catalog")
def update_catalog():
    client_gs = gspread.authorize(CREDS)
    sheet = client_gs.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
    records = sheet.get_all_records()

    client = OpenAI()
    products = []
    for r in records:
        text = f"{r['שם מוצר']} {r.get('תיאור','')} {r.get('קטגוריה','')} {r.get('מותג','')}"
        emb = client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        ).data[0].embedding
        products.append({"meta": r, "embedding": emb})

    with open(OUTPUT_PATH, "w", encoding="utf8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

    return jsonify({
        "status": "ok",
        "count": len(products),
        "updated": datetime.now().isoformat()
    })
