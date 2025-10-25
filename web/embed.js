(function () {
  const VERCEL_API_BASE = "https://shopipet-chatkit.vercel.app";

  const style = document.createElement("style");
  style.innerHTML = `
  .shopibot-bubble {
    position: fixed;
    bottom: 20px;
    right: 20px;
    width: 60px;
    height: 60px;
    border-radius: 50%;
    background-color: #25d366;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 4px 20px rgba(0,0,0,0.25);
    cursor: pointer;
    z-index: 1000000;
    transition: transform 0.2s ease;
  }
  .shopibot-bubble:hover { transform: scale(1.1); }
  .shopibot-bubble svg { width: 28px; height: 28px; fill: #fff; }

  .shopibot-panel {
    position: fixed;
    bottom: 90px;
    right: 20px;
    width: 400px;
    max-width: 90vw;
    height: 600px;
    max-height: 85vh;
    display: none;
    flex-direction: column;
    background: #e5ddd5;
    border-radius: 16px;
    overflow: hidden;
    box-shadow: 0 8px 40px rgba(0,0,0,0.25);
    font-family: 'Helvetica Neue', sans-serif;
    z-index: 999999;
    animation: fadeIn 0.3s ease;
  }
  @keyframes fadeIn { from {opacity:0;transform:translateY(10px);} to {opacity:1;transform:translateY(0);} }

  .shopibot-header {
    background: #075e54;
    color: white;
    padding: 12px 16px;
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .shopibot-header img {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    object-fit: cover;
  }
  .shopibot-header span { flex: 1; font-weight: 600; }
  .shopibot-close {
    cursor: pointer;
    font-size: 20px;
    font-weight: bold;
  }

  .shopibot-body {
    flex: 1;
    overflow-y: auto;
    padding: 10px;
    display: flex;
    flex-direction: column;
    background: #efeae2;
  }

  .msg {
    max-width: 80%;
    padding: 10px 14px;
    border-radius: 12px;
    margin: 6px 0;
    word-wrap: break-word;
    font-size: 14px;
    line-height: 1.4;
  }
  .msg.user { background: #dcf8c6; align-self: flex-end; border-bottom-right-radius: 2px; }
  .msg.bot { background: white; align-self: flex-start; border-bottom-left-radius: 2px; }

  .shopibot-input {
    display: flex;
    padding: 8px;
    background: #f0f0f0;
    border-top: 1px solid #ddd;
  }
  .shopibot-input input {
    flex: 1;
    padding: 10px;
    border: none;
    border-radius: 20px;
    outline: none;
  }
  .shopibot-input button {
    background: #25d366;
    border: none;
    color: white;
    border-radius: 50%;
    width: 44px;
    height: 44px;
    margin-left: 8px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .shopibot-input button svg { width: 22px; height: 22px; }

  .prod {
    display: flex;
    gap: 10px;
    background: #fff;
    border-radius: 10px;
    margin: 8px 0;
    overflow: hidden;
  }
  .prod img { width: 60px; height: 60px; object-fit: cover; }
  .prod .meta { padding: 6px; font-size: 13px; }

  @media (max-width: 600px) {
    .shopibot-panel {
      width: 100%;
      height: 100%;
      bottom: 0;
      right: 0;
      border-radius: 0;
    }
    .shopibot-bubble { bottom: 15px; right: 15px; }
  }
  `;
  document.head.appendChild(style);

  // === יצירת האלמנטים ===
  const bubble = document.createElement("div");
  bubble.className = "shopibot-bubble";
  bubble.innerHTML = `<svg viewBox="0 0 24 24"><path d="M12 3C7.03 3 3 6.92 3 11.5c0 2.45 1.23 4.65 3.18 6.11L5 21l3.7-1.42C9.63 19.86 10.79 20 12 20c4.97 0 9-3.92 9-8.5S16.97 3 12 3z"/></svg>`;

  const panel = document.createElement("div");
  panel.className = "shopibot-panel";
  panel.innerHTML = `
    <div class="shopibot-header">
      <img src="https://dev.shopipet.co.il/wp-content/uploads/2025/01/shopipet-logo-circle.png" alt="ShopiPet">
      <span>ShopiBot 🐾</span>
      <div class="shopibot-close">&times;</div>
    </div>
    <div class="shopibot-body" id="chat-body"></div>
    <div class="shopibot-input">
      <input id="chat-input" placeholder="כתוב הודעה..." />
      <button id="chat-send">
        <svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
      </button>
    </div>
  `;
  document.body.appendChild(bubble);
  document.body.appendChild(panel);

  const body = panel.querySelector("#chat-body");
  const input = panel.querySelector("#chat-input");
  const send = panel.querySelector("#chat-send");
  const close = panel.querySelector(".shopibot-close");

  function toggleChat(open) {
    panel.style.display = open ? "flex" : "none";
    if (open) addBot("שלום! איך אפשר לעזור? 😊");
  }

  bubble.addEventListener("click", () => toggleChat(true));
  close.addEventListener("click", () => toggleChat(false));

  function addMsg(text, cls) {
    const el = document.createElement("div");
    el.className = "msg " + cls;
    el.textContent = text;
    body.appendChild(el);
    body.scrollTop = body.scrollHeight;
  }
  function addBot(text) { addMsg(text, "bot"); }
  function addUser(text) { addMsg(text, "user"); }

  function addProducts(items) {
    items.forEach(p => {
      const wrap = document.createElement("div");
      wrap.className = "prod";
      wrap.innerHTML = `
        <img src="${p.image || ''}" alt="${p.name || ''}" />
        <div class="meta">
          <div><strong>${p.name || ''}</strong></div>
          <div>${p.description || ''}</div>
          <div><b>${p.price ? '₪' + p.price : ''}</b></div>
        </div>
      `;
      body.appendChild(wrap);
    });
    body.scrollTop = body.scrollHeight;
  }

  async function ask(q) {
    addUser(q);
    addBot("מחפש בשבילך...");
    try {
      const res = await fetch(`${VERCEL_API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: q, limit: 5 })
      });
      const data = await res.json();
      const last = body.querySelector(".msg.bot:last-child");
      if (last) last.remove();
      addBot(data.message || "הנה מה שמצאתי:");
      if (data.items?.length) addProducts(data.items);
    } catch {
      addBot("😕 הייתה בעיה זמנית, נסה שוב עוד רגע.");
    }
  }

  send.addEventListener("click", () => {
    const q = input.value.trim();
    if (!q) return;
    input.value = "";
    ask(q);
  });
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") send.click(); });
})();
