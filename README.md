# ShopiBot • ChatKit-ready (WooCommerce + Google Sheets + ChatGPT)

This project gives you a production-ready API and a minimal floating web chat to run on **shopipet.co.il**.
- **Backend**: FastAPI on Vercel
- **Data**: Google Sheets (ID: `1-XfEIXT0ovbhkWnBezc4v2xIcmUdONC7mAcep9554q8`)
- **LLM**: OpenAI (ChatGPT) via `OPENAI_API_KEY`
- **Frontend**: simple chat bubble for WooCommerce (or swap with ChatKit widget)

## 1) Deploy to Vercel
Upload this folder as a new Vercel project. Then set Environment Variables:
- `GOOGLE_CREDENTIALS` — paste your Service Account JSON (full content)
- `OPENAI_API_KEY` — your OpenAI API key
- `SPREADSHEET_ID` — `1-XfEIXT0ovbhkWnBezc4v2xIcmUdONC7mAcep9554q8`
- `SHEET_RANGE` — e.g. `Products!A2:F` (replace *Products* with the tab name from your sheet link)

Endpoints after deploy:
- `GET /api/ping`
- `GET /api/search?q=cat`
- `POST /api/chat` with JSON `{"message":"אני צריך מזון לגור כלבים"}`

## 2) Connect to WooCommerce
Add `web/embed.js` to your theme footer or with a plugin like "Insert Headers and Footers".
Before publishing, edit `VERCEL_API_BASE` inside `web/embed.js` to your domain, e.g.:
```
const VERCEL_API_BASE = 'https://shopipet-chat.vercel.app';
```

## 3) (Optional) Use ChatKit
If you prefer official ChatKit UI widgets, include the ChatKit script on your site and in the action handler call your API:
```js
chatkit.setOptions({
  widgets: {
    async onAction(action) {
      const res = await fetch('https://YOUR-VERCEL-DOMAIN.vercel.app/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: action.input || action.query || '' })
      });
      const data = await res.json();
      // Render data.items as cards (name, price, image) using ChatKit ListView/Card widgets
    }
  }
});
```

## Sheet Format
Expected columns (A..F):
`ID | Product Name | Category | Price | Description | Image URL`

## Local Dev
```
pip install -r requirements.txt
export GOOGLE_CREDENTIALS='{...service account json...}'
export OPENAI_API_KEY='sk-...'
export SPREADSHEET_ID='1-XfEIXT0ovbhkWnBezc4v2xIcmUdONC7mAcep9554q8'
export SHEET_RANGE='Sheet1!A2:F'
uvicorn api.chat:app --port 8000
```
Visit `http://localhost:8000/api/ping` and test `POST /api/chat`.

---

**Tip**: Share the sheet with your Service Account email as *Viewer* or *Editor*.
