from fastapi import FastAPI, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from googleapiclient.discovery import build
from google.oauth2 import service_account
from openai import OpenAI
import os, json

app = FastAPI(title="ShopiBot Chat API")

# CORS for website use
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://dev.shopipet.co.il",
        "https://shopipet.co.il",
        "https://www.shopipet.co.il"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Environment configuration ===
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "1-XfEIXT0ovbhkWnBezc4v2xIcmUdONC7mAcep9554q8")
SHEET_RANGE = os.environ.get("SHEET_RANGE", "Sheet1!A2:F")  # e.g., Products!A2:F
GOOGLE_CREDENTIALS = os.environ.get("GOOGLE_CREDENTIALS")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

if not GOOGLE_CREDENTIALS:
    raise RuntimeError("Missing GOOGLE_CREDENTIALS env (paste your Service Account JSON).")
if not OPENAI_API_KEY:
    raise RuntimeError("Missing OPENAI_API_KEY env.")

# Google Sheets client
try:
    service_account_info = json.loads(GOOGLE_CREDENTIALS)
except Exception as e:
    raise RuntimeError("GOOGLE_CREDENTIALS must contain valid JSON.") from e

creds = service_account.Credentials.from_service_account_info(
    service_account_info,
    scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
)

def fetch_rows():
    service = build("sheets", "v4", credentials=creds)
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=SHEET_RANGE).execute()
    return result.get("values", [])

# OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

@app.get("/api/ping")
def ping():
    return {"ok": True, "message": "ShopiBot (Chat+Sheets) is alive"}

@app.get("/api/search")
def search_products(q: str = Query("", description="Free-text search across product fields"), limit: int = 8):
    rows = fetch_rows()
    ql = q.lower().strip()
    results = []
    for r in rows:
        r = (r + [""] * 6)[:6]
        pid, name, category, price, desc, img = r
        hay = " ".join([pid, name, category, price, desc]).lower()
        if ql in hay or ql == "":
            results.append({
                "id": pid, "name": name, "category": category,
                "price": price, "description": desc, "image": img
            })
        if len(results) >= limit:
            break
    return {"query": q, "count": len(results), "items": results}

class ChatRequest(BaseModel):
    message: str
    limit: int | None = 5
    filters: dict | None = None  # e.g., {"category": "Dog", "max_price": 100}

@app.post("/api/chat")
def chat(req: ChatRequest):
    # 1) Pull products (simple filter over the sheet)
    rows = fetch_rows()
    items = []
    for r in rows:
        r = (r + [""] * 6)[:6]
        pid, name, category, price, desc, img = r
        # basic filtering
        try:
            price_f = float(str(price).replace(",", "").replace("₪", "").strip())
        except Exception:
            price_f = None
        ok = True
        if req.filters:
            if "category" in req.filters and req.filters["category"]:
                if str(category).lower().strip() != str(req.filters["category"]).lower().strip():
                    ok = False
            if "max_price" in req.filters and req.filters["max_price"] and price_f is not None:
                if price_f > float(req.filters["max_price"]):
                    ok = False
        if not ok:
            continue
        # free-text match bonus
        ql = req.message.lower()
        hay = " ".join([pid, name, category, str(price), desc]).lower()
        score = 1
        if ql and ql in hay:
            score += 2
        items.append({
            "id": pid, "name": name, "category": category,
            "price": price, "description": desc, "image": img, "score": score
        })
        if len(items) >= max(20, (req.limit or 5) * 2):
            break

    # sort by score (rough relevance)
    items.sort(key=lambda x: x.get("score", 0), reverse=True)
    top_items = items[: (req.limit or 5)]

    # 2) Ask OpenAI to produce a helpful answer
    system_prompt = (
        "You are ShopiBot, a helpful assistant for a pet supply store. "
        "Answer clearly and concisely. If appropriate, reference 3-5 recommended products provided in the tool data. "
        "ALWAYS prefer factual details from the provided products. Prices are in ILS. Keep tone warm and friendly."
    )
    products_for_llm = [
        {"id": i["id"], "name": i["name"], "category": i["category"], "price": i["price"], "description": i["description"]}
        for i in top_items
    ]

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": req.message},
        {"role": "system", "content": "Candidate products (JSON): " + json.dumps(products_for_llm, ensure_ascii=False)}
    ]

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.4
    )

    reply = completion.choices[0].message.content if completion.choices else "I'm here to help."
    # 3) Return both the LLM reply and structured products (so frontend can render cards or ChatKit widgets) 
    return {
        "message": reply,
        "items": top_items
    }
