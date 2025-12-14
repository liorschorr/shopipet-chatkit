# Phase 2 Deployment Guide

## 🚀 Quick Deployment Steps

### 1. Pre-Deployment Checklist

- [ ] All environment variables set in Vercel
- [ ] OpenAI Assistant has `show_products` function configured
- [ ] Redis URL configured (optional but recommended)
- [ ] Test locally first

### 2. Deploy to Vercel

```bash
# Install Vercel CLI if needed
npm i -g vercel

# Deploy
vercel deploy

# Or deploy to production
vercel --prod
```

### 3. Post-Deployment Steps

#### A. Sync the Catalog

```bash
# Get your Vercel URL from deployment output
curl https://your-app.vercel.app/api/sync
```

Expected response:
```json
{
  "status": "success",
  "message": "Catalog synced successfully",
  "products_count": 150,
  "vector_store_id": "vs_...",
  "skipped": false
}
```

#### B. Test Streaming Endpoint

```bash
curl -N https://your-app.vercel.app/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "שלום", "thread_id": null}'
```

You should see streaming SSE events.

#### C. Test on Your Website

1. Embed the widget on a test page
2. Open browser console
3. Send a message
4. Watch for streaming events in console
5. Verify products display correctly

---

## Environment Variables

Set these in Vercel Dashboard → Settings → Environment Variables:

```bash
# Required
OPENAI_API_KEY=sk-...
OPENAI_ASSISTANT_ID=asst_...
WOO_BASE_URL=https://your-store.com
WOO_CONSUMER_KEY=ck_...
WOO_CONSUMER_SECRET=cs_...

# Optional (Recommended)
REDIS_URL=redis://...
```

---

## Rollback Plan

If streaming has issues, you can instantly rollback to polling:

### Option 1: Frontend Toggle (Quick)

In `public/embed.js`, change line 1369:
```javascript
const USE_STREAMING = false;  // Switch back to polling
```

Redeploy just the frontend.

### Option 2: Use Old Endpoint

Frontend can call `/api/chat` (polling) instead of `/api/chat/stream`.

Both endpoints are available simultaneously!

---

## Monitoring

### Check Logs

**Vercel Dashboard:**
1. Go to your project
2. Click "Deployments"
3. Click latest deployment
4. Click "Functions" tab
5. Click `api/index` function
6. View logs

### Common Issues

#### "AssistantStream object has no attribute __aenter__"
**Cause**: Old OpenAI library
**Fix**: Ensure `openai==1.57.0` in requirements.txt (already set)

#### "Missing REDIS_URL"
**Status**: Warning only, not critical
**Impact**: Sync will upload every time (no hash checking)
**Fix**: Add Redis (see OPENAI_SETUP_GUIDE.md)

#### "Streaming events not arriving"
**Possible causes**:
1. Vercel edge network buffering (rare)
2. OpenAI Assistant misconfigured
3. Model doesn't support streaming

**Debug**:
```bash
# Test locally first
uvicorn api.index:app --reload
curl -N http://localhost:8000/api/chat/stream -H "Content-Type: application/json" -d '{"message":"test"}'
```

---

## Performance Monitoring

### Before vs After Metrics

Track these in your analytics:

**Response Time:**
- Polling: 3-10 seconds until first text
- Streaming: <1 second until first character

**User Engagement:**
- Streaming should increase message completion rates
- Lower bounce on slow responses

**Server Load:**
- Polling: Multiple requests per message (0.5s intervals)
- Streaming: Single connection per message

---

## Gradual Rollout Strategy

### Phase A: Internal Testing (Day 1)
```javascript
// embed.js
const USE_STREAMING = location.hostname === 'staging.yourstore.com';
```

### Phase B: Beta Users (Day 2-3)
```javascript
const USE_STREAMING = Math.random() < 0.1; // 10% of users
```

### Phase C: Full Rollout (Day 4+)
```javascript
const USE_STREAMING = true; // Everyone
```

---

## Cron Job Update

The sync endpoint is called daily at 2 AM via Vercel cron.

**Current configuration** (vercel.json):
```json
{
  "crons": [
    {
      "path": "/api/sync",
      "schedule": "0 2 * * *"
    }
  ]
}
```

This will:
1. Check Redis hash
2. Skip if catalog unchanged
3. Upload only if products changed

**Logs**: Check Vercel → Deployments → Cron Jobs tab

---

## Cost Considerations

### OpenAI API Costs

**Streaming vs Polling**: Same cost (tokens used are identical)

**Smart Sync Savings**:
- Without Redis: Uploads catalog daily (even if unchanged)
- With Redis: Uploads only when products change
- **Savings**: ~30 uploads/month → ~2-3 uploads/month
- **Vector Store cost**: $0.10/GB/day

### Vercel Costs

**Function Execution**:
- Polling: ~500-1000ms per message
- Streaming: ~500-1000ms per message (similar)

**Bandwidth**:
- Polling: Single JSON response
- Streaming: Multiple SSE chunks (slightly more bandwidth)

**Verdict**: Costs are nearly identical, but UX is much better with streaming.

---

## Security Checklist

- [ ] CORS configured properly (only your domains)
- [ ] API keys in environment variables (not code)
- [ ] Error traces disabled in production (check api/index.py)
- [ ] Redis connection uses TLS (if using external Redis)
- [ ] Rate limiting configured (Phase 3)

---

## Success Criteria

After deployment, verify:

✅ Health endpoint returns "healthy"
✅ Sync endpoint completes successfully
✅ Streaming chat works on test page
✅ Products display correctly
✅ Error messages show gracefully
✅ No console errors in browser
✅ Mobile works smoothly
✅ Conversation persists across page loads

---

## Quick Reference

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Health check |
| `/api/health` | GET | Detailed health |
| `/api/chat` | POST | Chat (polling) |
| `/api/chat/stream` | POST | Chat (streaming) |
| `/api/sync` | GET | Sync catalog |
| `/docs` | GET | API documentation |

### Files Changed

```
✅ requirements.txt - Added FastAPI, Redis
✅ vercel.json - Routes to api/index.py
✅ api/index.py - Main FastAPI app
✅ api/models.py - Pydantic models
✅ api/chat_router.py - Polling endpoint
✅ api/chat_streaming.py - Streaming endpoint
✅ api/sync_router.py - Smart sync
✅ utils/products.py - Centralized formatting
✅ public/embed.js - Streaming support
```

### Old Files (Can Delete After Testing)

```
⚠️ api/chat.py - Old polling handler
⚠️ api/sync.py - Old sync handler
```

Keep these for 1-2 weeks during testing, then remove.

---

## Next Phase Preview

**Phase 3: Security & Architecture**
- XSS sanitization in frontend
- Rate limiting
- Error categorization
- Structured logging

**Phase 4: UX Polish**
- Session recovery
- Enhanced typing indicators
- Message retry
- Offline handling

---

## Support

**Documentation:**
- [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) - Full migration overview
- [OPENAI_SETUP_GUIDE.md](OPENAI_SETUP_GUIDE.md) - OpenAI configuration
- `/docs` endpoint - Interactive API docs

**Logs:**
- Vercel Dashboard → Functions → Logs
- Browser Console (F12)

**Testing:**
- Local: `uvicorn api.index:app --reload`
- Staging: Use feature flags in embed.js
