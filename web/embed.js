(function () {
  const VERCEL_API_BASE = 'https://shopipet-chatkit.vercel.app';

  const style = document.createElement('style');
  style.innerHTML = `
  .shopibot-bubble{position:fixed;bottom:24px;right:24px;width:56px;height:56px;border-radius:50%;background:#2b65d9;color:#fff;display:flex;align-items:center;justify-content:center;cursor:pointer;box-shadow:0 8px 24px rgba(0,0,0,.18);z-index:999999;transition:transform 0.2s}
  .shopibot-bubble:hover{transform:scale(1.1)}
  .shopibot-panel{position:fixed;bottom:92px;right:24px;width:360px;max-width:92vw;height:520px;background:#fff;border-radius:16px;box-shadow:0 16px 40px rgba(0,0,0,.22);display:none;flex-direction:column;overflow:hidden;z-index:999998}
  .shopibot-header{padding:12px 14px;background:#2b65d9;color:#fff;font-weight:600;display:flex;justify-content:space-between;align-items:center}
  .shopibot-close{cursor:pointer;font-size:20px;padding:0 4px}
  .shopibot-body{padding:12px;overflow-y:auto;height:100%;display:flex;flex-direction:column;gap:8px}
  .shopibot-input{display:flex;gap:8px;padding:12px;border-top:1px solid #eee}
  .shopibot-input input{flex:1;padding:10px;border:1px solid #ddd;border-radius:10px;font-size:14px}
  .shopibot-input button{padding:10px 14px;border:none;border-radius:10px;background:#2b65d9;color:#fff;cursor:pointer;font-weight:600}
  .shopibot-input button:hover{background:#1e4db8}
  .msg{margin:4px 0;padding:10px 12px;border-radius:12px;max-width:85%;font-size:14px;line-height:1.4}
  .msg.user{background:#f1f5ff;margin-left:auto;text-align:right}
  .msg.bot{background:#f7f7f7}
  .msg.loading{background:#f0f0f0;color:#999;font-style:italic}
  .prod{display:flex;gap:10px;border:1px solid #e5e5e5;padding:10px;border-radius:12px;margin:6px 0;cursor:pointer;transition:all 0.2s;text-decoration:none;color:inherit}
  .prod:hover{border-color:#2b65d9;box-shadow:0 2px 8px rgba(43,101,217,0.1);transform:translateY(-2px)}
  .prod img{width:70px;height:70px;object-fit:cover;border-radius:8px}
  .prod .meta{flex:1;font-size:13px}
  .prod .name{font-weight:600;margin-bottom:4px;color:#333}
  .prod .brand{color:#666;font-size:12px;margin-bottom:4px}
  .prod .desc{color:#666;font-size:12px;line-height:1.3;margin-bottom:4px}
  .prod .price{font-weight:700;color:#2b65d9;font-size:15px}
  `;
  document.head.appendChild(style);

  const bubble = document.createElement('div');
  bubble.className = 'shopibot-bubble';
  bubble.innerHTML = '💬';
  
  const panel = document.createElement('div');
  panel.className = 'shopibot-panel';
  panel.innerHTML = `
    <div class="shopibot-header">
      <span>ShopiBot • עוזר לבעלי חיים</span>
      <span class="shopibot-close">×</span>
    </div>
    <div class="shopibot-body" id="shopibot-body"></div>
    <div class="shopibot-input">
      <input id="shopibot-input" placeholder="מה אתה מחפש היום?" />
      <button id="shopibot-send">שלח</button>
    </div>
  `;
  
  document.body.appendChild(bubble);
  document.body.appendChild(panel);

  const body = panel.querySelector('#shopibot-body');
  const input = panel.querySelector('#shopibot-input');
  const send = panel.querySelector('#shopibot-send');
  const closeBtn = panel.querySelector('.shopibot-close');

  function toggle(){ 
    panel.style.display = panel.style.display==='flex' ? 'none' : 'flex'; 
    if (panel.style.display === 'flex') {
      input.focus();
    }
  }
  
  bubble.addEventListener('click', () => {
    if (panel.style.display !== 'flex') {
      panel.style.display = 'flex';
      if (body.children.length === 0) {
        addBot("שלום! איך אפשר לעזור? ספר לי על החיה שלך ומה אתה מחפש.");
      }
      input.focus();
    } else {
      toggle();
    }
  });

  closeBtn.addEventListener('click', toggle);

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
  
  function addLoading(){
    const el = document.createElement('div');
    el.className = 'msg loading';
    el.textContent = 'מחפש בשבילך...';
    el.id = 'loading-msg';
    body.appendChild(el);
    body.scrollTop = body.scrollHeight;
    return el;
  }
  
  function removeLoading(){
    const loading = document.getElementById('loading-msg');
    if (loading) loading.remove();
  }
  
  function addProducts(items){
    items.forEach(p => {
      const wrap = document.createElement('a');
      wrap.className = 'prod';
      wrap.href = p.url || '#';
      wrap.target = p.url ? '_blank' : '_self';
      
      const imgSrc = p.image || 'https://via.placeholder.com/70?text=No+Image';
      const brandText = p.brand ? `<div class="brand">🏷️ ${p.brand}</div>` : '';
      const priceText = p.price ? `₪${p.price}` : '';
      
      wrap.innerHTML = `
        <img src="${imgSrc}" alt="${p.name || ''}" onerror="this.src='https://via.placeholder.com/70?text=No+Image'" />
        <div class="meta">
          <div class="name">${p.name || ''}</div>
          ${brandText}
          <div class="desc">${(p.description || '').substring(0, 60)}${p.description && p.description.length > 60 ? '...' : ''}</div>
          <div class="price">${priceText}</div>
        </div>
      `;
      
      body.appendChild(wrap);
    });
    body.scrollTop = body.scrollHeight;
  }

  async function ask(q){
    addUser(q);
    const loading = addLoading();
    
    try{
      const res = await fetch(VERCEL_API_BASE + '/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: q, limit: 5 })
      });
      
      const data = await res.json();
      removeLoading();
      
      addBot(data.message || 'הנה התוצאות שמצאתי.');
      if (data.items && data.items.length) {
        addProducts(data.items);
      } else {
        addBot('מצטער, לא מצאתי מוצרים מתאימים. נסה חיפוש אחר או שאל אותי על מוצרים ספציפיים.');
      }
    } catch(e) {
      removeLoading();
      console.error('ShopiBot Error:', e);
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
    if (e.key === 'Enter') send.click();
  });
})();
