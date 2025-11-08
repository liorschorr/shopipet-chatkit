import os
import json
import traceback
import time
import numpy as np
from numpy.linalg import norm
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import gspread
from google.oauth2.service_account import Credentials
from openai import OpenAI
import redis

# =============================
# CONFIGURATION
# =============================
app = Flask(__name__)
CORS(app)

SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")
GOOGLE_CREDENTIALS = os.environ.get("GOOGLE_CREDENTIALS")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
KV_URL = os.environ.get("shopipetbot_REDIS_URL")  # יתכן שתשנה בהתאם ל-Vercel שלך

openai_client = OpenAI(api_key=OPENAI_API_KEY)

product_catalog_embeddings = []

# =============================
# HELPERS
# =============================

def get_embedding(text: str):
    """Generate embedding for a given text"""
    response = openai_client.embeddings.create(
        model="text-embedding-3-large",  # מודל מדויק יותר לעברית
        input=text
    )
    return response.data[0].embedding

def format_product(meta, score):
    """Normalize product data before returning to frontend"""
    return {
        "id": meta.get("id"),
        "name": meta.get("name"),
        "category": meta.get("category"),
        "price": meta.get("sale_price") or meta.get("regular_price"),
        "regular_price": meta.get("regular_price"),
        "sale_price": meta.get("sale_price"),
        "description": meta.get("short_description") or meta.get("description"),
        "image": meta.get("image_url"),
        "brand": meta.get("brand"),
        "url": meta.get("url"),
        "sku": meta.get("sku"),
        "score": round(float(score), 3)
    }

# =============================
# CATALOG HANDLING
# =============================

def load_smart_catalog():
    """Load product catalog embeddings from Redis memory"""
    global product_catalog_embeddings
    try:
        if not KV_URL:
            print("❌ Missing KV/Redis URL")
            return False
        r = redis.from_url(KV_URL)
        raw = r.get("shopipet_catalog_embeddings")
        if not raw:
            print("⚠️ No catalog found in KV.")
            return False
        data = json.loads(raw)
        for item in data:
            emb = np.array(item["embedding"], dtype=np.float32)
            item["embedding_np"] = emb
        product_catalog_embeddings = data
        print(f"✅ Loaded {len(product_catalog_embeddings)} products into memory.")
        return True
    except Exception as e:
        print(f"❌ Error loading catalog: {e}")
        return False

# טען מיד עם עליית השרת
load_smart_catalog()

# =============================
# SMART SEARCH (EMBEDDINGS)
# =============================

def find_products_by_embedding(query, limit=5, threshold=0.25):
    """Find products using embedding similarity"""
    if not product_catalog_embeddings:
        raise Exception("Smart catalog not loaded")

    query_emb = np.array(get_embedding(query), dtype=np.float32)

    results = []
    for item in product_catalog_embeddings:
        sim = np.dot(query_emb, item["embedding_np"]) / (norm(query_emb) * norm(item["embedding_np"]))
        if sim > threshold:  # החזר רק תוצאות עם דמיון אמיתי
            results.append({"product": item["meta"], "score": float(sim)})

    results.sort(key=lambda x: x["score"], reverse=True)
    top = [format_product(res["product"], res["score"]) for res in results[:limit]]
    return top

# =============================
# RESPONSE GENERATION
# =============================

def get_llm_response(message, products):
    """Generate friendly text reply, only based on catalog results"""
    if not products:
        return "לא מצאתי מוצרים מתאימים בקטלוג שלנו 🐾 נסה לנסח אחרת או להשתמש במילות מפתח שונות."

    try:
        summary = "\n".join([
            f"- {p['name']} ({p.get('brand','')}) - ₪{p.get('price','')}"
            for p in products[:5]
        ])
        prompt = f"""
אתה שופיבוט - עוזר וירטואלי של חנות ShopiPet למוצרי חיות מחמד.
השאלה: "{message}"
מצאתי את המוצרים הבאים:
{summary}
כתוב תשובה קצרה (עד 2 משפטים), ידידותית וברורה, שמתבססת רק על המוצרים שמופיעים ברשימה.
אל תמציא מוצרים חדשים או תענה על נושאים שלא קשורים לחיות מחמד.
"""
        resp = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.7
        )
        reply = resp.choices[0].message.content.strip()
        return reply
    except Exception as e:
        print(f"⚠️ get_llm_response error: {e}")
        return f"מצאתי {len(products)} מוצרים מתאימים בקטלוג שלנו 🐾"

# =============================
# ROUTES
# =============================

@app.route("/api/ping", methods=["GET"])
def ping():
    return jsonify({
        "status": "ok",
        "message": "ShopiBot API Ping ✅",
        "smart_catalog_items": len(product_catalog_embeddings),
        "storage": "Vercel KV" if KV_URL else "None"
    })

@app.route("/api/chat", methods=["POST"])
def chat():
    try:
        body = request.get_json() or {}
        message = body.get("message", "").strip()
        if not message:
            return jsonify({"message": "מה תרצה לחפש היום? 🐶", "items": []})

        if not product_catalog_embeddings:
            load_smart_catalog()

        items = find_products_by_embedding(message, limit=5)
        reply = get_llm_response(message, items)
        return jsonify({"message": reply, "items": items, "source": "smart_catalog"})

    except Exception as e:
        print(f"❌ /api/chat error: {e}")
        traceback.print_exc()
        return jsonify({"message": "אירעה שגיאה פנימית", "error": str(e)}), 500

# =============================
# STATIC FILES
# =============================

@app.route("/web/<path:filename>")
def serve_web(filename):
    return send_from_directory(os.path.join(app.root_path, "..", "web"), filename)

@app.route("/public/<path:filename>")
def serve_public(filename):
    return send_from_directory(os.path.join(app.root_path, "..", "public"), filename)

# =============================
# ENTRY POINT
# =============================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
