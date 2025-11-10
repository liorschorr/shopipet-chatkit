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
from urllib.parse import urlparse, parse_qs

app = Flask(__name__)
CORS(app)

# ====== ENV ======
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
KV_URL = os.environ.get("shopipetbot_REDIS_URL")  # או קונפיג משלך ל-Redis/Vercel KV
SITE_BASE_URL = os.environ.get("WOO_BASE_URL", "").rstrip("/") # למשל: https://dev.shopipet.co.il

# לקוח OpenAI
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# זיכרון של הקטלוג (מגיע מה-KV)
product_catalog_embeddings = []  # כל פריט: {"meta": {...}, "embedding": [...], "embedding_np": np.ndarray }


# ====== עזרי URL ======
def extract_product_id_from_url(u: str):
    """ניסיון לחלץ מזהה מוצר 'p' מכתובת מוצר קיימת"""
    try:
        q = parse_qs(urlparse(u).query)
        pid = q.get("p", [None])[0]
        return str(pid) if pid else None
    except Exception:
        return None


def is_search_url(u: str):
    try:
        return "?s=" in u
    except Exception:
        return False


def normalize_product_url(meta: dict, site_base: str):
    """
    מחזיר URL מוצר ישיר (לא חיפוש) לפי הסדר:
    1) אם meta.url מכיל p= — נחלץ את ה-ID ונבנה URL חדש על בסיס SITE_BASE_URL
    2) אם meta.id קיים — נבנה URL חדש על בסיס SITE_BASE_URL
    3) אחרת נחזיר את meta.url (אם קיים ולא חיפוש), ואם לא — None
    """
    base = site_base or ""  # יכול להיות ריק בלוקאלי
    raw_url = (meta.get("url") or "").strip()
    pid = None

    if raw_url:
        if is_search_url(raw_url):
            pid = meta.get("id")
        else:
            pid = extract_product_id_from_url(raw_url)
            if not pid:
                # אולי יש id במטה
                pid = meta.get("id")
    else:
        pid = meta.get("id")

    if pid:
        return f"{base}/product/?p={pid}".replace("//product", "/product") if base else f"/product/?p={pid}"

    # אין לנו מזהה — אם יש URL שאינו חיפוש, נחזיר אותו כמו שהוא
    if raw_url and not is_search_url(raw_url):
        # אם יש base ואותו דומיין לא תואם — נרצה להחליף? לרוב עדיף להשאיר כמות שהוא
        return raw_url

    return None


def build_add_to_cart_url(pid: str, site_base: str):
    if not pid:
        return None
    base = site_base or ""
    return f"{base}/?add-to-cart={pid}" if base else f"/?add-to-cart={pid}"


def looks_like_variants(meta: dict):
    """
    אינדיקציה חלשה לוריאציות (אם אין לך עמודות Sheet מסודרות).
    עוד אפשרות: תוסיף עמודה 'type' או 'has_variants' ב-Sheet ותשתמש בה כאן במקום ההשערה.
    """
    text = f"{meta.get('name','')} {meta.get('short_description','')} {meta.get('description','')}"
    hints = ["בחר", "בחירת", "מידה", "טעם", "Size", "Option", "Variation"]
    return any(h in text for h in hints)


# ====== Embeddings ======
def get_embedding(text: str):
    resp = openai_client.embeddings.create(
        model="text-embedding-3-large",  # מדויק יותר לעברית
        input=text.replace("\n", " ")
    )
    return resp.data[0].embedding


def format_product(meta: dict, score: float):
    pid = meta.get("id")
    product_url = normalize_product_url(meta, SITE_BASE_URL)
    has_vars = looks_like_variants(meta)
    add_to_cart = build_add_to_cart_url(pid, SITE_BASE_URL) if not has_vars else product_url

    return {
        "id": pid,
        "name": meta.get("name"),
        "brand": meta.get("brand"),
        "category": meta.get("category"),
        "price": meta.get("sale_price") or meta.get("regular_price"),
        "regular_price": meta.get("regular_price"),
        "sale_price": meta.get("sale_price"),
        "description": meta.get("short_description") or meta.get("description"),
        "image": meta.get("image_url"),
        "url": product_url,
        "add_to_cart_url": add_to_cart,
        "has_variants": has_vars,
        "score": round(float(score), 3),
    }


# ====== טעינת קטלוג מה-KV ======
def load_smart_catalog():
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
        # הוסף numpy vector לכל פריט
        for item in data:
            emb = np.array(item["embedding"], dtype=np.float32)
            item["embedding_np"] = emb
        product_catalog_embeddings = data
        print(f"✅ Loaded {len(product_catalog_embeddings)} products into memory.")
        return True
    except Exception as e:
        print(f"❌ Error loading catalog: {e}")
        return False


# טען מיד בהעלאה
load_smart_catalog()


# ====== חיפוש חכם ======
def find_products_by_embedding(query: str, limit=5, threshold=0.25):
    if not product_catalog_embeddings:
        raise Exception("Smart catalog not loaded")

    q_emb = np.array(get_embedding(query), dtype=np.float32)

    results = []
    for item in product_catalog_embeddings:
        sim = float(np.dot(q_emb, item["embedding_np"]) / (norm(q_emb) * norm(item["embedding_np"])))
        if sim > threshold:
            results.append({"product": item["meta"], "score": sim})

    results.sort(key=lambda x: x["score"], reverse=True)
    return [format_product(r["product"], r["score"]) for r in results[:limit]]


# ====== ניסוח תשובה (רק על סמך הקטלוג) ======
def get_llm_response(message: str, products: list):
    if not products:
        return "לא מצאתי מוצרים מתאימים בקטלוג שלנו 🐾 נסה לנסח אחרת."

    summary = "\n".join(
        [f"- {p['name']} ({p.get('brand','')}) — ₪{p.get('price','')}" for p in products]
    )
    prompt = f"""
אתה שופיבוט של ShopiPet.
השאלה: "{message}"
המוצרים שנמצאו:
{summary}
ענה בעברית, בקצרה ובידידותיות (עד 2 משפטים), רק על סמך המוצרים שמופיעים למעלה.
אל תמציא מוצרים, אל תייצר קישורים בעצמך — הלקוח יקבל את הקישורים מהשרת.
"""

    try:
        resp = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=120,
            temperature=0.6,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print("⚠️ LLM error:", e)
        return f"מצאתי {len(products)} מוצרים מתאימים 🐾"


# ====== ראוטים ======
@app.route("/api/chat", methods=["POST"])
def chat():
    try:
        body = request.get_json() or {}
        message = (body.get("message") or "").strip()
        if not message:
            return jsonify({"message": "מה תרצה לחפש היום? 🐶", "items": []})

        if not product_catalog_embeddings:
            load_smart_catalog()

        items = find_products_by_embedding(message, limit=5, threshold=0.25)
        reply = get_llm_response(message, items)
        return jsonify({"message": reply, "items": items, "source": "smart_catalog"})
    except Exception as e:
        print("❌ /api/chat error:", e)
        traceback.print_exc()
        return jsonify({"message": "שגיאה פנימית", "error": str(e)}), 500


@app.route("/api/ping", methods=["GET"])
def ping():
    return jsonify({
        "status": "ok",
        "message": "ShopiBot API Ping ✅",
        "smart_catalog_items": len(product_catalog_embeddings),
        "site_base_url": SITE_BASE_URL or "(relative)",
        "storage": "Redis/Vercel KV" if KV_URL else "None"
    })


@app.route("/web/<path:filename>")
def serve_web(filename):
    return send_from_directory(os.path.join(app.root_path, "..", "web"), filename)


@app.route("/public/<path:filename>")
def serve_public(filename):
    return send_from_directory(os.path.join(app.root_path, "..", "public"), filename)

@app.route("/api/update-catalog", methods=["GET", "POST"])
def update_catalog():

    """
    מקבל JSON עם קטלוג מעודכן ושומר אותו בזיכרון וגם ב-Redis (אם מוגדר KV_URL)
    """
    global product_catalog_embeddings
    try:
        data = request.get_json(force=True)
        if not data or "items" not in data:
            return jsonify({"error": "Missing 'items' key"}), 400

        items = data["items"]
        for item in items:
            emb = np.array(item["embedding"], dtype=np.float32)
            item["embedding_np"] = emb

        product_catalog_embeddings = items
        print(f"✅ Catalog updated: {len(items)} items in memory.")

        if KV_URL:
            r = redis.from_url(KV_URL)
            r.set("shopipet_catalog_embeddings", json.dumps(items, ensure_ascii=False))
            print("✅ Saved to Redis")

        return jsonify({
            "status": "ok",
            "message": f"Catalog updated with {len(items)} items",
            "stored_in": "Redis" if KV_URL else "Memory only"
        })
    except Exception as e:
        print("❌ /api/update-catalog error:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
