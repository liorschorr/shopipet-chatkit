# ShopiPet ChatKit - FastAPI Migration Guide

## Phase 1: Infrastructure Upgrade ✅ COMPLETED

### What We've Built

#### 1. **Updated Dependencies** ([requirements.txt](requirements.txt))
```
✅ FastAPI 0.115.5 - Modern async web framework
✅ Uvicorn 0.32.1 - ASGI server
✅ Pydantic 2.10.3 - Data validation
✅ Redis 5.2.0 - Caching (for Phase 2)
```

#### 2. **Main Entry Point** ([api/index.py](api/index.py))
- FastAPI application with CORS middleware
- Global exception handler (sanitizes errors, hides tracebacks from users)
- Health check endpoints (`/`, `/api`, `/api/health`)
- Router registration for chat and sync endpoints

**Key Features:**
- ✅ CORS configured (allow all for now)
- ✅ Global error handling
- ✅ Environment variable validation
- ✅ Ready for router imports

#### 3. **Pydantic Models** ([api/models.py](api/models.py))
```python
ChatRequest - Validates incoming messages
ChatResponse - Standardized chat responses
Product - Product display model
ProductVariation - Variation details
SyncResponse - Sync operation results
ErrorResponse - Error formatting
```

**Benefits:**
- ✅ Automatic request validation
- ✅ Type safety
- ✅ Auto-generated API docs
- ✅ Clear contracts between frontend/backend

#### 4. **Chat Router** ([api/chat_router.py](api/chat_router.py))
- Converted from `BaseHTTPRequestHandler` to FastAPI `APIRouter`
- Uses async/await patterns
- Modular helper functions (`get_openai_client`, `get_woocommerce_api`, `fetch_products`)
- Still uses **polling** (will be upgraded to streaming in Phase 2)

**Improvements Over Original:**
- ✅ Clean separation of concerns
- ✅ Better error handling
- ✅ Type-safe request/response
- ✅ Easier to test
- ✅ Ready for streaming upgrade

#### 5. **Updated Vercel Configuration** ([vercel.json](vercel.json))
- Points all routes to `api/index.py`
- Single entry point for FastAPI app
- Maintains cron job for sync endpoint

---

## Current Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                              │
│                     (public/embed.js)                        │
└─────────────────┬───────────────────────────────────────────┘
                  │ POST /api/chat
                  ↓
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI App                              │
│                   (api/index.py)                             │
├─────────────────────────────────────────────────────────────┤
│  - CORS Middleware                                           │
│  - Global Exception Handler                                  │
│  - Router Registration                                       │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ↓
┌─────────────────────────────────────────────────────────────┐
│                   Chat Router                                │
│               (api/chat_router.py)                           │
├─────────────────────────────────────────────────────────────┤
│  1. Validate request (Pydantic)                              │
│  2. Create/get OpenAI thread                                 │
│  3. Add user message                                         │
│  4. Create run                                               │
│  5. Poll for completion (⚠️ POLLING - will be streaming)     │
│  6. Handle tool calls (show_products)                        │
│  7. Return response                                          │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ↓
┌────────────────────────────┬────────────────────────────────┐
│      OpenAI Assistant      │      WooCommerce API           │
│  - Thread management       │  - Product fetching            │
│  - AI responses            │  - Variations                  │
│  - Tool calling            │  - Pricing                     │
└────────────────────────────┴────────────────────────────────┘
```

---

## Migration Status

### ✅ Phase 1: Infrastructure Upgrade (COMPLETE)
- [x] Update requirements.txt
- [x] Create FastAPI entry point (api/index.py)
- [x] Define Pydantic models
- [x] Convert chat.py to FastAPI router
- [x] Update vercel.json for ASGI

### 🔄 Phase 2: Performance & Streaming (NEXT)
- [ ] Replace polling with OpenAI streaming
- [ ] Implement FastAPI StreamingResponse
- [ ] Update frontend to handle streams
- [ ] Add smart sync with Redis hashing
- [ ] Create utility module (utils/products.py)

### 📋 Phase 3: Architecture & Security (PENDING)
- [ ] Centralize product formatting logic
- [ ] Frontend XSS sanitization
- [ ] Environment variable validation
- [ ] Rate limiting

### 📋 Phase 4: UX Polish (PENDING)
- [ ] Real-time typing indicators
- [ ] Session recovery endpoint
- [ ] Enhanced error messages

---

## Testing Phase 1

### Local Testing

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Set environment variables:**
```bash
export OPENAI_API_KEY="your_key"
export OPENAI_ASSISTANT_ID="asst_..."
export WOO_BASE_URL="https://your-store.com"
export WOO_CONSUMER_KEY="ck_..."
export WOO_CONSUMER_SECRET="cs_..."
```

3. **Run locally:**
```bash
uvicorn api.index:app --reload --port 8000
```

4. **Test endpoints:**
```bash
# Health check
curl http://localhost:8000/api/health

# Chat endpoint
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "מוצרים לכלבים", "thread_id": null}'
```

### Vercel Deployment

```bash
vercel deploy
```

---

## Breaking Changes

### For Developers

**Old (BaseHTTPRequestHandler):**
```python
class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # Manual header management
        # Manual JSON parsing
        # No type validation
```

**New (FastAPI):**
```python
@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    # Automatic validation
    # Type safety
    # Clean async/await
```

### For Frontend

**No changes required!** The API contract remains the same:

**Request:**
```json
{
  "message": "string",
  "thread_id": "string | null"
}
```

**Response:**
```json
{
  "reply": "string",
  "thread_id": "string",
  "action": "show_products | null",
  "products": [...]
}
```

---

## What's Next?

### Immediate Next Steps (Phase 2)

1. **Implement Streaming** - Replace the polling loop with:
```python
async with client.beta.threads.runs.stream(...) as stream:
    async for event in stream:
        # Yield deltas to frontend
```

2. **Update Frontend** - Handle streaming in embed.js:
```javascript
const response = await fetch('/api/chat', {...});
const reader = response.body.getReader();
// Process stream chunks
```

3. **Smart Sync** - Add Redis caching:
```python
import hashlib
catalog_hash = hashlib.md5(catalog_text.encode()).hexdigest()
if redis.get("catalog_hash") == catalog_hash:
    return {"status": "skipped"}
```

---

## File Structure

```
shopipet-chatkit/
├── api/
│   ├── index.py          ✅ NEW - FastAPI entry point
│   ├── models.py         ✅ NEW - Pydantic models
│   ├── chat_router.py    ✅ NEW - Chat endpoint (FastAPI)
│   ├── chat.py           ⚠️  OLD - Keep for reference, will be removed
│   └── sync.py           📝 TODO - Convert to FastAPI router
├── public/
│   └── embed.js          📝 TODO - Update for streaming (Phase 2)
├── requirements.txt      ✅ UPDATED
├── vercel.json          ✅ UPDATED
└── MIGRATION_GUIDE.md   ✅ NEW - This file
```

---

## Benefits Achieved So Far

### Developer Experience
✅ Type safety with Pydantic
✅ Auto-generated API docs at `/docs`
✅ Better error messages
✅ Easier testing and debugging
✅ Modern async/await patterns

### Performance (Prepared For)
✅ Ready for streaming (Phase 2)
✅ Redis integration prepared
✅ Scalable architecture

### Security
✅ Global exception handler (no trace leaks)
✅ Request validation
✅ CORS configured

---

## Known Issues & Limitations

1. **Still Using Polling** - Phase 1 maintains polling behavior. Streaming comes in Phase 2.
2. **No Redis Yet** - Smart sync with hash comparison will be added in Phase 2.
3. **Old Files Present** - Original `chat.py` and `sync.py` are still present for reference.

---

## Questions or Issues?

- Check `/docs` endpoint for auto-generated API documentation
- Review logs in Vercel dashboard
- Test health endpoint: `/api/health`

---

**Migration Progress: 25% Complete** 🚀
**Next Phase: Streaming Implementation**
