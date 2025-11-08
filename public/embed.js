 (() => {
  // בסיס ה-API של האתר שלך (לא של Vercel)
const API_BASE = "";

  // שומר גם את דומיין האתר שבו נטען הווידג'ט (לשימוש פנימי)
  const ORIGIN = window.location.origin.replace(/\/$/, ""); // dev או www לפי האתר

  const container = document.createElement("div");
  container.id = "shopipet-chat";
  container.style.position = "fixed";
  container.style.bottom = "90px";
  container.style.right = "20px";
  container.style.width = "380px";
  container.style.maxHeight = "70vh";
  container.style.background = "#fff";
  container.style.borderRadius = "20px";
  container.style.boxShadow = "0 6px 18px rgba(0,0,0,0.15)";
  container.style.overflow = "hidden";
  container.style.display = "none";
  container.style.zIndex = "999999";
  container.style.fontFamily = "'Heebo', sans-serif";
  document.body.appendChild(container);


  const toggleBtn = document.createElement("div");
  toggleBtn.innerHTML = `
    <div style="
      position: fixed; bottom: 20px; right: 20px;
      width: 64px; height: 64px; border-radius: 50%;
      background: #ffd600; display: flex; align-items: center; justify-content: center;
      box-shadow: 0 3px 10px rgba(0,0,0,0.25); cursor: pointer; z-index: 999999;">
      <img src="https://cdn-icons-png.flaticon.com/512/616/616408.png" style="width:38px;height:38px;">
    </div>`;
  document.body.appendChild(toggleBtn);

  toggleBtn.addEventListener("click", () => {
    container.style.display = container.style.display === "none" ? "flex" : "none";
  });

  container.innerHTML = `
    <div style="flex-direction:column;display:flex;width:100%;height:100%;">
      <div style="background:#f7f1fa;padding:10px;text-align:center;font-weight:600;color:#333;border-bottom:1px solid #eee;">
        שופיבוט • עזרה לבעלי חיים
      </div>
      <div id="chat-body" style="flex:1;padding:10px;overflow-y:auto;direction:rtl;"></div>
      <div style="border-top:1px solid #eee;padding:10px;display:flex;gap:8px;">
        <input id="chat-input" type="text" placeholder="מה אתה מחפש היום?" style="flex:1;padding:10px;border-radius:12px;border:1px solid #ccc;font-family:inherit;">
        <button id="chat-send" style="background:#ffd600;border:none;padding:10px 16px;border-radius:12px;font-weight:600;cursor:pointer;">שלח</button>
      </div>
    </div>
  `;

  const chatBody = container.querySelector("#chat-body");
  const input = container.querySelector("#chat-input");
  const sendBtn = container.querySelector("#chat-send");

  const appendMessage = (text, from = "bot") => {
    const msg = document.createElement("div");
    msg.style.margin = "8px 0";
    msg.style.direction = "rtl";
    msg.style.textAlign = from === "bot" ? "right" : "left";
    msg.style.background = from === "bot" ? "#f9f9f9" : "#e1ffc7";
    msg.style.padding = "8px 12px";
    msg.style.borderRadius = "12px";
    msg.style.display = "inline-block";
    msg.style.maxWidth = "90%";
    msg.innerHTML = text;
    chatBody.appendChild(msg);
    chatBody.scrollTop = chatBody.scrollHeight;
  };

  const normalizeItemUrls = (p) => {
    const safeId = p.id;
    const isSearch = p.url && p.url.includes("?s=");
    const hasPid = p.url && /[?&]p=\d+/.test(p.url);
    // תמיד נכפה דומיין נוכחי
    if (hasPid) {
      const pid = new URL(p.url, ORIGIN).searchParams.get("p");
      p.url = `${ORIGIN}/product/?p=${pid}`;
    } else if (safeId) {
      p.url = `${ORIGIN}/product/?p=${safeId}`;
    }
    // add-to-cart
    if (safeId && p.has_variants === false) {
      p.add_to_cart_url = `${ORIGIN}/?add-to-cart=${safeId}`;
    } else if (safeId && (!p.add_to_cart_url || isSearch)) {
      p.add_to_cart_url = `${ORIGIN}/product/?p=${safeId}`;
    }
    return p;
  };

  const appendProducts = (items) => {
    items.map(normalizeItemUrls).forEach((p) => {
      const card = document.createElement("div");
      card.style.border = "1px solid #eee";
      card.style.borderRadius = "12px";
      card.style.padding = "10px";
      card.style.margin = "8px 0";
      card.style.display = "flex";
      card.style.gap = "10px";
      card.style.alignItems = "flex-start";
      card.style.direction = "rtl";

      const price = p.price ? `₪${p.price}` : "";
      const btnHtml = p.has_variants
        ? `<a href="${p.url}" target="_blank"
             style="background:#fff;border:1px solid #ccc;border-radius:8px;padding:6px 10px;font-size:13px;text-decoration:none;color:#333;">
             בחר אפשרויות</a>`
        : `<a href="${p.add_to_cart_url || p.url}" target="_blank"
             style="background:#ffd600;border:none;border-radius:8px;padding:6px 10px;font-size:13px;text-decoration:none;color:#000;font-weight:600;">
             הוסף לסל</a>`;

      card.innerHTML = `
        <img src="${p.image || "https://via.placeholder.com/80"}"
             style="width:80px;height:80px;object-fit:cover;border-radius:10px;flex-shrink:0;">
        <div style="flex:1">
          <div style="font-weight:600;color:#333;margin-bottom:4px;">${p.name || ""}</div>
          <div style="font-size:13px;color:#555;margin-bottom:6px;">${p.description || ""}</div>
          <div style="font-weight:600;margin-bottom:6px;">${price}</div>
          ${btnHtml}
        </div>`;
      chatBody.appendChild(card);
    });
    chatBody.scrollTop = chatBody.scrollHeight;
  };

  const sendMessage = async () => {
    const text = input.value.trim();
    if (!text) return;
    appendMessage(text, "user");
    input.value = "";
    appendMessage("⏳ חושב...");

    try {
const res = await fetch(`${API_BASE}/api/chat`, {
  method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });
      const data = await res.json();
      chatBody.removeChild(chatBody.lastChild);
      appendMessage(data.message || "לא התקבלה תשובה.");
      if (data.items && data.items.length) appendProducts(data.items);
    } catch (err) {
      appendMessage("❌ שגיאה בשרת, נסה שוב מאוחר יותר.");
      console.error(err);
    }
  };

  sendBtn.addEventListener("click", sendMessage);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendMessage();
  });
})();
