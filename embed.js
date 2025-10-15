(function () {
  // Minimal floating chat for WooCommerce that calls /api/chat on your Vercel domain.
  const VERCEL_API_BASE = 'https://YOUR-VERCEL-DOMAIN.vercel.app';

  const style = document.createElement('style');
  style.innerHTML = `
  .shopibot-bubble{position:fixed;bottom:24px;right:24px;width:56px;height:56px;border-radius:50%;background:#2b65d9;color:#fff;display:flex;align-items:center;justify-content:center;cursor:pointer;box-shadow:0 8px 24px rgba(0,0,0,.18);z-index:999999}
  .shopibot-panel{position:fixed;bottom:92px;right:24px;width:360px;max-width:92vw;height:520px;background:#fff;border-radius:16px;box-shadow:0 16px 40px rgba(0,0,0,.22);display:none;flex-direction:column;overflow:hidden;z-index:999998}
  .shopibot-header{padding:12px 14px;background:#2b65d9;color:#fff;font-weight:600}
  .shopibot-body{padding:12px;overflow-y:auto;height:100%}
  .shopibot-input{display:flex;gap:8px;padding:12px;border-top:1px solid #eee}
  .shopibot-input input{flex:1;padding:10px;border:1px solid #ddd;border-radius:10px}
  .shopibot-input button{padding:10px 14px;border:none;border-radius:10px;background:#2b65d9;color:#fff;cursor:pointer}
  .msg{margin:8px 0;padding:8px 10px;border-radius:10px;max-width:85%}
  .msg.user{background:#f1f5ff;margin-left:auto}
  .msg.bot{background:#f7f7f7}
  .prod{display:flex;gap:10px;border:1px solid #eee;padding:8px;border-radius:10px;margin:6px 0}
  .prod img{width:64px;height:64px;object-fit:cover;border-radius:8px}
  .prod .meta{font-size:13px}
  `;
  document.head.appendChild(style);

  const bubble = document.createElement('div');
  bubble.className = 'shopibot-bubble';
  bubble.innerHTML = '💬';
  const panel = document.createElement('div');
  panel.className = 'shopibot-panel';
  panel.innerHTML = `
    <div class="shopibot-header">ShopiBot • עזרה לבעלי חיים</div>
    <div class="shopibot-body" id="shopibot-body"></div>
    <div class="shopibot-input">
      <input id="shopibot-input" placeholder="מה אתה מחפש היום?" />
      <button id="shopibot-send">שלח</button>
    </div>
  `;
  document.body.appendChild(bubble);
  document.body.appendChild(panel);

  function toggle(){ panel.style.display = panel.style.display==='flex' ? 'none' : 'flex'; }
  bubble.addEventListener('click', () => {
    if (panel.style.display !== 'flex') {
      panel.style.display = 'flex';
      addBot("שלום! איך אפשר לעזור? ספר לי על החיה שלך ומה אתה מחפש.");
    } else toggle();
  });

  const body = panel.querySelector('#shopibot-body');
  const input = panel.querySelector('#shopibot-input');
  const send = panel.querySelector('#shopibot-send');

  function addUser(text){
    const el = document.createElement('div');
    el.className = 'msg user';
    el.textContent = text;
    body.appendChild(el);
    body.scrollTop = body.scrollHeight;
  }
  function addBot(text){
    const el = document.createElement('div');
    el.className = 'msg bot';
    el.textContent = text;
    body.appendChild(el);
    body.scrollTop = body.scrollHeight;
  }
  function addProducts(items){
    items.forEach(p => {
      const wrap = document.createElement('div');
      wrap.className = 'prod';
      wrap.innerHTML = `
        <img src="${p.image || ''}" alt="${p.name || ''}" />
        <div class="meta">
          <div><strong>${p.name || ''}</strong></div>
          <div>${p.description || ''}</div>
          <div><b>${p.price ? '₪'+p.price : ''}</b></div>
        </div>
      `;
      body.appendChild(wrap);
    });
    body.scrollTop = body.scrollHeight;
  }

  async function ask(q){
    addUser(q);
    addBot('מחפש בשבילך...');
    try{
      const res = await fetch(VERCEL_API_BASE + '/api/chat', {
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ message: q, limit: 5 }})
      });
      const data = await res.json();
      const last = body.querySelector('.msg.bot:last-child');
      if (last) last.remove();
      addBot(data.message || 'הנה התוצאות שמצאתי.');
      if (data.items && data.items.length) addProducts(data.items);
    }catch(e){
      addBot('הייתה בעיה זמנית. נסה שוב בעוד רגע.');
    }
  }

  send.addEventListener('click', () => {
    const q = input.value.trim();
    if (!q) return;
    input.value = '';
    ask(q);
  });
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {{ send.click(); }}
  });
})();