import os
import json
import traceback
import time
import numpy as np
from numpy.linalg import norm
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from openai import OpenAI
import redis

app = Flask(__name__)
CORS(app)

SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")
GOOGLE_CREDENTIALS = os.environ.get("GOOGLE_CREDENTIALS")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
KV_URL = os.environ.get("shopipetbot_REDIS_URL")

openai_client = OpenAI(api_key=OPENAI_API_KEY)
product_catalog_embeddings = []

# =========================
# UTILITIES
# =========================
def get_embedding(text: str):
    resp = openai_client.embeddings.create(
        model="text-embedding-3-large",
        input=text
    )
    return resp.data[0].embedding

def format_product(meta, score):
    """Normalize and enrich product data"""
    base_url = "https://www.shopipet.co.il/product/?p="
    product_id = meta.get("id")

    product_url = meta.get("url")
    if not product_url or "?" not in product_url:
        product_url = f"{base_url}{product_id}"

    has_variants = "בחר" in (meta.get("name", "") + meta.get("description", ""))
    add_to_cart_url = (
        f"https://www.shopipet.co.il/?add-to-cart={product_id}"
        if not has_variants
        else product_url
    )

    return {
        "id": product_id,
        "name": meta.get("name"),
        "category": meta.get("category"),
        "price": meta.get("sale_price") or meta.get("regular_price"),
        "regular_price": meta.get("regular_price"),
        "sale_price": meta.get("sale_price"),
        "description": meta.get("short_description") or meta.get("description"),
        "image": meta.get("image_url"),
        "brand": meta.get("brand"),
        "url": product_url,
        "add_to_cart_url": add_to_cart_url,
        "has_variants": has_variants,
        "score": round(float(score), 3)
    }

# =========================
# LOAD CATALOG
# =========================
def load_smart_catalog():
    global product_catalog_embeddings
    try:
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
        print(f"✅ Loaded {len(product_catalog_embeddings)} products.")
        return True
    except Exception as e:
        print(f"❌ Catalog load error: {e}")
        return False

load_smart_catalog()

# =========================
# SMART SEARCH
# =========================
def find_products_by_embedding(query, limit=5, threshold=0.25):
    if not product_catalog_embeddings:
        raise Exception("Catalog not loaded")

    query_emb = np.array(get_embedding(query), dtype=np.float32)
    results = []
    for item in product_catalog_embeddings:
        sim = np.dot(query_emb, item["embedding_np"]) / (norm(query_emb) * norm(item["embedding_np"]))
        if sim > threshold:
            results.append({"product": item["meta"], "score": float(sim)})

    results.sort(key=lambda x: x["score"], reverse=True)
    return [format_product(res["product"], res["score"]) for res in results[:limit]]

# =========================
# RESPONSE
# =========================
def get_llm_response(message, products):
    if not products:
        return "לא מצאתי מוצרים מתאימים בקטלוג שלנו 🐾 נסה לנסח אחרת."

    summary = "\n".join([
        f"- {p['name']} ({p.get('brand','')}) - ₪{p.get('price','')}"
        for p in products
    ])
    prompt = f"""
אתה שופיבוט של ShopiPet.
השאלה: "{message}"
המוצרים שנמצאו:
{summary}
ענה בעברית, בקצרה ובידידותיות (עד 2 משפטים), רק על סמך המוצרים שמופיעים למעלה.
"""
    try:
        resp = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=120,
            temperature=0.7
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print("⚠️ LLM error:", e)
        return f"מצאתי {len(products)} מוצרים מתאימים 🐾"

# =========================
# ROUTES
# =========================
@app.route("/api/chat", methods=["POST"])
def chat():
    body = request.get_json() or {}
    message = body.get("message", "").strip()
    if not message:
        return jsonify({"message": "מה תרצה לחפש היום? 🐶", "items": []})

    try:
        products = find_products_by_embedding(message)
        reply = get_llm_response(message, products)
        return jsonify({"message": reply, "items": products, "source": "smart_catalog"})
    except Exception as e:
        print("❌ Error:", e)
        traceback.print_exc()
        return jsonify({"message": "שגיאה פנימית", "error": str(e)}), 500

@app.route("/api/ping", methods=["GET"])
def ping():
    return jsonify({
        "status": "ok",
        "message": "ShopiBot API ✅",
        "catalog_items": len(product_catalog_embeddings)
    })

@app.route("/web/<path:filename>")
def web_file(filename):
    return send_from_directory(os.path.join(app.root_path, "..", "web"), filename)

@app.route("/public/<path:filename>")
def public_file(filename):
    return send_from_directory(os.path.join(app.root_path, "..", "public"), filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
