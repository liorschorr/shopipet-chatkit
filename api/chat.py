from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from googleapiclient.discovery import build
from google.oauth2 import service_account
from openai import OpenAI
from mangum import Mangum
import os, json

# === Create the FastAPI app ===
app = FastAPI(title="ShopiBot Chat API")

# === CORS Configuration ===
origins = [
    "https://dev.shopipet.co.il",
    "https://shopipet.co.il",
    "https://www.shopipet.co.il",
    "http://localhost:3000",
    "*"  # בשלב פיתוח - הסר בייצור
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Environment configuration ===
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "1-XfEIXT0ovbhkWnBezc4v2xIcmUdONC7mAcep9554q8")
SHEET_RANGE = os.environ.get("SHEET_RANGE", "Sheet1!A2:F")
GOOGLE_CREDENTIALS = os.environ.get("GOOGLE_CREDENTIALS")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Initialize clients (with error handling)
creds = None
client = None

try:
    if GOOGLE_CREDENTIALS:
        service_account_info = json.loads(GOOGLE_CREDENTIALS)
        creds = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
except Exception as e:
    print(f"Error loading Google credentials: {e}")

if OPENAI_API_KEY:
    client = OpenAI(api_key=OPENAI_API_KEY)

def fetch_rows():
    if not creds:
        return []
    try:
        service = build("sheets", "v4", credentials=creds)
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=SHEET_RANGE).execute()
        return result.get("values", [])
    except Exception as e:
        print(f"Error fetching rows: {e}")
        return []

@app.get("/")
@app.get("/api")
def root():
    return {"status": "ok", "message": "ShopiBot API is running"}

@app.get("/api/ping")
def ping():
    return {"ok": True, "message": "ShopiBot (Chat+Sheets) is alive"}

@app.get("/api/search")
def search_products(q: str = Query("", description="Free-text search"), limit: int = 8):
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
    filters: dict | None = None

@app.post("/api/chat")
def chat(req: ChatRequest):
    if not client:
        return {"message": "OpenAI client not configured", "items": []}
    
    # 1) Fetch and filter products
    rows = fetch_rows()
    items = []
    
    for r in rows:
        r = (r + [""] * 6)[:6]
        pid, name, category, price, desc, img = r
        
        # Parse price
        try:
            price_f = float(str(price).replace(",", "").replace("₪", "").strip())
        except:
            price_f = None
        
        # Apply filters
        ok = True
        if req.filters:
            if "category" in req.filters and req.filters["category"]:
                if str(category).lower().strip() != str(req.filters["category"]).lower().strip():
                    ok = False
            if "max_price" in req.filters and req.filters["max_price"] and price_f:
                if price_f > float(req.filters["max_price"]):
                    ok = False
        
        if not ok:
            continue
        
        # Text matching score
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
    
    # Sort by relevance
    items.sort(key=lambda x: x.get("score", 0), reverse=True)
    top_items = items[:(req.limit or 5)]
    
    # 2) Get LLM response
    system_prompt = (
        "You are ShopiBot, a helpful assistant for a pet supply store. "
        "Answer clearly and concisely in Hebrew. Reference recommended products when relevant. "
        "Prices are in ILS (₪). Keep tone warm and friendly."
    )
    
    products_for_llm = [
        {"id": i["id"], "name": i["name"], "category": i["category"], 
         "price": i["price"], "description": i["description"]}
        for i in top_items
    ]
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": req.message},
        {"role": "system", "content": "Available products: " + json.dumps(products_for_llm, ensure_ascii=False)}
    ]
    
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.4
        )
        reply = completion.choices[0].message.content if completion.choices else "אני כאן לעזור!"
    except Exception as e:
        print(f"OpenAI error: {e}")
        reply = "סליחה, יש לי בעיה זמנית. נסה שוב בעוד רגע."
    
    return {
        "message": reply,
        "items": top_items
    }

# === Vercel Handler ===
handler = Mangum(app)
