# OpenAI Assistant API Setup Guide for Streaming

## Overview

This guide will help you configure the OpenAI Assistant API for streaming responses with the ShopiPet ChatKit.

---

## Step-by-Step Configuration

### 1. OpenAI API Key ✅ (Already Have)

You should already have:
- `OPENAI_API_KEY` environment variable set
- `OPENAI_ASSISTANT_ID` environment variable set

---

### 2. Verify Assistant Configuration

#### Check Your Assistant Settings

1. Go to https://platform.openai.com/assistants
2. Find your assistant (ID should match `OPENAI_ASSISTANT_ID`)
3. Verify these settings:

**Model**: `gpt-4-turbo-preview` or `gpt-4-1106-preview` (supports streaming)
**Tools**: Should include:
- ✅ File Search (for catalog)
- ✅ Function: `show_products`

---

### 3. Function Tool Configuration

Your assistant needs the `show_products` function defined. Here's the exact configuration:

```json
{
  "name": "show_products",
  "description": "Display product cards to the user. Call this when the user asks about specific products or when you want to show product recommendations.",
  "parameters": {
    "type": "object",
    "properties": {
      "product_ids": {
        "type": "array",
        "items": {
          "type": "integer"
        },
        "description": "Array of WooCommerce product IDs (System_ID from catalog) to display"
      }
    },
    "required": ["product_ids"]
  }
}
```

#### How to Add/Update the Function:

1. Go to your Assistant in OpenAI Platform
2. Scroll to "Functions" section
3. Click "Add function" or edit existing `show_products`
4. Paste the JSON above
5. Save

---

### 4. Vector Store Setup

Your assistant should already have a Vector Store attached from the sync script.

To verify:
1. Go to your Assistant page
2. Check "Tools" section
3. Under "File search", you should see a Vector Store ID
4. Click it to see the catalog file

If missing, run the sync endpoint: `GET /api/sync`

---

### 5. Test Streaming (No OpenAI Changes Needed!)

**Good news**: The OpenAI Assistants API supports streaming by default. No additional configuration needed in the OpenAI dashboard.

The streaming happens on the **client side** (our code), using:
```python
client.beta.threads.runs.stream(...)
```

---

## Environment Variables Checklist

Make sure these are set in your environment (Vercel, local, etc.):

```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-...                    # Your API key
OPENAI_ASSISTANT_ID=asst_...             # Your assistant ID

# WooCommerce Configuration
WOO_BASE_URL=https://your-store.com
WOO_CONSUMER_KEY=ck_...
WOO_CONSUMER_SECRET=cs_...

# Optional: Redis for Smart Sync
REDIS_URL=redis://...                    # Optional, enables hash checking
```

---

## Testing Checklist

### Local Testing

1. **Start the server:**
```bash
uvicorn api.index:app --reload --port 8000
```

2. **Test health endpoint:**
```bash
curl http://localhost:8000/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "environment": "configured",
  "missing_vars": null
}
```

3. **Test streaming endpoint:**
```bash
curl -N http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "שלום", "thread_id": null}'
```

You should see streaming events like:
```
data: {"type":"thread_id","thread_id":"thread_..."}

data: {"type":"text","content":"ש"}

data: {"type":"text","content":"לום"}

data: {"type":"done","thread_id":"thread_..."}
```

4. **Test with product request:**
```bash
curl -N http://localhost:8000/api/chat/stream \
  -H "Content-Type": application/json" \
  -d '{"message": "מזון לכלבים", "thread_id": null}'
```

Should eventually return:
```
data: {"type":"products","data":[...]}
```

---

## Frontend Testing

1. **Open the widget** in your browser
2. **Type a message** - should see streaming text appear character by character
3. **Request products** - try "מזון לכלבים"
4. **Check console** - should see streaming events logged

### Toggle Streaming vs Polling

In `embed.js`, change this line:
```javascript
const USE_STREAMING = true;  // Set to false to use old polling method
```

This lets you test both approaches.

---

## Troubleshooting

### Issue: "Missing OPENAI_ASSISTANT_ID"
**Solution**: Set the environment variable in Vercel/your environment

### Issue: "AssistantStream has no attribute '__aenter__'"
**Solution**: Update openai library: `pip install --upgrade openai>=1.14.0`

### Issue: "No streaming events received"
**Solution**:
1. Check that your OpenAI model supports streaming (gpt-4-turbo does)
2. Verify network isn't buffering responses
3. Check Vercel logs for errors

### Issue: "Function 'show_products' not found"
**Solution**: Add the function to your Assistant (see Step 3 above)

### Issue: "Catalog not found"
**Solution**: Run sync endpoint: `curl http://localhost:8000/api/sync`

---

## Redis Configuration (Optional but Recommended)

Redis enables smart sync that skips uploads when catalog hasn't changed.

### Vercel Redis (Recommended)

1. Go to your Vercel project
2. Click "Storage" tab
3. Create "KV Database" (free tier available)
4. Vercel automatically sets `REDIS_URL` environment variable

### Alternative Redis Providers

- **Upstash**: https://upstash.com (free tier)
- **Redis Cloud**: https://redis.com/try-free

Add the connection URL as `REDIS_URL` environment variable.

### Test Redis Integration

```bash
curl http://localhost:8000/api/sync
```

First run:
```json
{
  "status": "success",
  "message": "Catalog synced successfully",
  "skipped": false,
  "hash": "a1b2c3..."
}
```

Second run (no changes):
```json
{
  "status": "skipped",
  "message": "Catalog unchanged since last sync",
  "skipped": true,
  "hash": "a1b2c3..."
}
```

---

## Performance Comparison

### Before (Polling):
- ⏱️ User waits 3-10 seconds for response
- 🔄 Backend polls every 0.5s (resource intensive)
- ⚠️ Can timeout on complex queries

### After (Streaming):
- ⚡ Text appears in real-time (feels instant)
- 🎯 Single connection, efficient
- ✅ No timeouts (data streams as generated)
- 🚀 Better UX - typing indicator shows immediately

---

## Next Steps

After Phase 2 is working:

1. **Phase 3**: XSS sanitization, centralized error handling
2. **Phase 4**: Session recovery, enhanced UX
3. **Monitoring**: Add logging/analytics for streaming events
4. **Optimization**: Tune chunk sizes, add compression

---

## API Documentation

Once deployed, visit:
- `/docs` - Interactive API documentation (Swagger UI)
- `/redoc` - Alternative API docs (ReDoc)

These are auto-generated from your FastAPI code!

---

## Summary

**What you need to do manually in OpenAI:**
1. ✅ Verify `show_products` function is configured (Step 3)
2. ✅ Confirm model supports streaming (gpt-4-turbo)
3. ✅ Check Vector Store is attached

**What happens automatically:**
- ✅ Streaming is handled by our code
- ✅ Thread management
- ✅ Event processing
- ✅ Product tool calls

**That's it!** The OpenAI Assistants API supports streaming out of the box. Our FastAPI backend handles the streaming events and forwards them to the frontend.

---

## Questions?

Check the logs:
- **Local**: Terminal where uvicorn is running
- **Vercel**: Functions tab → Select function → Logs

Common log patterns:
- `Streaming error: ...` - Problem with OpenAI streaming
- `Failed to parse SSE event: ...` - Frontend parsing issue
- `WooCommerce API error: ...` - Product fetching problem
