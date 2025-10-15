(function () {
  const VERCEL_API_BASE = 'https://shopipet-chatkit.vercel.app';

  const style = document.createElement('style');
  style.innerHTML = `
  .shopibot-bubble{position:fixed;bottom:24px;right:24px;width:56px;height:56px;border-radius:50%;background:#2b65d9;color:#fff;display:flex;align-items:center;justify-content:center;cursor:pointer;box-shadow:0 8px 24px rgba(0,0,0,.18);z-index:999999;transition:transform 0.2s;font-size:24px}
  .shopibot-bubble:hover{transform:scale(1.1)}
  .shopibot-panel{position:fixed;bottom:92px;right:24px;width:360px;max-width:92vw;height:520px;background:#fff;border-radius:16px;box-shadow:0 16px 40px rgba(0,0,0,.22);display:none;flex-direction:column;overflow:hidden;z-index:999998}
  .shopibot-header{padding:12px 14px;background:#2b65d9;color:#fff;font-weight:600;display:flex;justify-content:space-between;align-items:center}
  .shopibot-close{cursor:pointer;font-size:24px;padding:0 4px;line-height:1}
  .shopibot-body{padding:12px;overflow-y:auto;height:100%;display:flex;flex-direction:column;gap:8px}
  .shopibot-input{display:flex;gap:8px;padding:12px;border-top:1px solid #eee}
  .shopibot-input input{flex:1;padding:10px;border:1px solid #ddd;border-radius:10px;font-size:14px;font-family:inherit}
  .shopibot-input button{padding:10px 14px;border:none;border-radius:10px;background:#2b65d9;color:#fff;cursor:pointer;font-weight:600;font-family:inherit}
  .shopibot-input button:hover{background:#1e4db8}
  .shopibot-input button:disabled{background:#ccc;cursor:not-allowed}
  .msg{margin:4px 0;padding:10px 12px;border-radius:12px;max-width:85%;font-size:14px;line-height:1.5}
  .msg.user{background:#f1f5ff;margin-left:auto;text-align:right}
  .msg.bot{background:#f7f7f7}
  .msg.loading{background:#f0f0f0;color:#999;font-style:italic}
  .prod{display:flex;gap:10px;border:1px solid #e5e5e5;padding:10px;border-radius:12px;margin:6px 0;cursor:pointer;transition:all 0.2s;text-decoration:none;color:inherit;background:#fff}
  .prod:hover{border-color:#2b65d9;box-shadow:0 2px 8px rgba(43,101,217,0.1);transform:translateY(-2px)}
  .prod img{width:70px;height:70px;object-fit:cover;border-radius:8px;flex-shrink:0}
  .prod .meta{flex:1;font-size:13px;min-width:0}
  .prod .name{font-weight:600;margin-bottom:4px;color:#333;line-height:1.3}
  .prod .brand{color:#666;font-size:12px;margin-bottom:4px}
  .prod .attrs{display:flex;flex-wrap:wrap;gap:4px;margin-bottom:6px}
  .prod .attr-tag{background:#e8f4ff;color:#2b65d9;font-size:11px;padding:2px 6px;border-radius:4px;white-space:nowrap}
  .prod .desc{color:#666;font-size:12px;line-height:1.3;margin-bottom:4px;overflow:hidden;text-overflow:ellipsis;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}
  .prod .price{font-weight:700;color:#2b65d9;font-size:15px}
  .quick-replies{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0}
  .quick-reply-btn{padding:8px 12px;border:1px solid #2b65d9;background:#fff;color:#2b65d9;border-radius:16px;font-size:13px;cursor:pointer;transition:all 0.2s;font-family:inherit}
  .quick-reply-btn:hover{background:#2b65d9;color:#fff}
  `;
  document.head.appendChild(style);

  const bubble = document.createElement('div');
  bubble.className = 'shopibot-bubble';
  bubble.innerHTML = '💬';
  bubble.title = 'פתח צ׳אט עם שופיבוט';
  
  const panel = document.createElement('div');
  panel.className = 'shopibot-panel';
  panel.innerHTML = `
    <div class="shopibot-header">
      <span>שופיבוט • עוזר קניות חכם</span>
      <span class="shopibot-close" title="סגור">×</span>
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
  
  let isLoading = false;

  function toggle(){ 
    panel.style.display = panel.style.display === 'flex' ? 'none' : 'flex'; 
    if (panel.style.display === 'flex') {
      input.focus();
    }
  }
  
  bubble.addEventListener('click', () => {
    if (panel.style.display !== 'flex') {
      panel.style.display = 'flex';
      if (body.children.length === 0) {
        addBot("שלום! 👋 אני שופיבוט, כאן כדי לעזור לך למצוא את המוצרים המושלמים לחיית המחמד שלך!");
        
        // Show quick category buttons
        setTimeout(() => {
          addQuickReplies([
            "🐕 מזון לכלבים",
            "🐈 מזון לחתולים",
            "🎾 צעצועים",
            "🛁 טיפוח"
          ]);
        }, 500);
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
    if (!items || items.length === 0) return;
    
    items.forEach(p => {
      const wrap = document.createElement('a');
      wrap.className = 'prod';
      wrap.href = p.url || '#';
      wrap.target = p.url ? '_blank' : '_self';
      wrap.rel = 'noopener noreferrer';
      
      const imgSrc = p.image || 'https://via.placeholder.com/70?text=No+Image';
      const brandText = p.brand ? `<div class="brand">🏷️ ${escapeHtml(p.brand)}</div>` : '';
      
      // Get first 2 non-empty attributes
      let attributesHtml = '';
      if (p.attributes && Array.isArray(p.attributes)) {
        const validAttrs = p.attributes.filter(attr => attr && attr.trim() !== '').slice(0, 2);
        if (validAttrs.length > 0) {
          attributesHtml = '<div class="attrs">';
          validAttrs.forEach(attr => {
            attributesHtml += `<span class="attr-tag">✓ ${escapeHtml(attr)}</span>`;
          });
          attributesHtml += '</div>';
        }
      }
      
      // Show sale price if available
      let priceHtml = '';
      if (p.sale_price && p.regular_price && p.sale_price !== p.regular_price) {
        priceHtml = `<div class="price">₪${escapeHtml(p.sale_price)} <span style="text-decoration:line-through;color:#999;font-size:12px">₪${escapeHtml(p.regular_price)}</span></div>`;
      } else {
        const price = p.price || p.regular_price || p.sale_price;
        priceHtml = price ? `<div class="price">₪${escapeHtml(price)}</div>` : '';
      }
      
      wrap.innerHTML = `
        <img src="${escapeHtml(imgSrc)}" alt="${escapeHtml(p.name || 'מוצר')}" onerror="this.src='https://via.placeholder.com/70?text=No+Image'" />
        <div class="meta">
          <div class="name">${escapeHtml(p.name || '')}</div>
          ${brandText}
          ${attributesHtml}
          <div class="desc">${escapeHtml((p.description || '').substring(0, 80))}${p.description && p.description.length > 80 ? '...' : ''}</div>
          ${priceHtml}
        </div>
      `;
      
      body.appendChild(wrap);
    });
    body.scrollTop = body.scrollHeight;
  }
  
  function addQuickReplies(options) {
    const container = document.createElement('div');
    container.className = 'quick-replies';
    container.style.cssText = 'display:flex;flex-wrap:wrap;gap:6px;margin:8px 0;';
    
    options.forEach(option => {
      const btn = document.createElement('button');
      btn.className = 'quick-reply-btn';
      btn.textContent = option;
      btn.style.cssText = 'padding:8px 12px;border:1px solid #2b65d9;background:#fff;color:#2b65d9;border-radius:16px;font-size:13px;cursor:pointer;transition:all 0.2s;font-family:inherit;';
      btn.onmouseover = () => {
        btn.style.background = '#2b65d9';
        btn.style.color = '#fff';
      };
      btn.onmouseout = () => {
        btn.style.background = '#fff';
        btn.style.color = '#2b65d9';
      };
      btn.onclick = () => {
        input.value = option.replace(/^[^\s]+\s/, ''); // Remove emoji
        send.click();
      };
      container.appendChild(btn);
    });
    
    body.appendChild(container);
    body.scrollTop = body.scrollHeight;
  }
  
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  async function ask(q){
    if (isLoading) return;
    
    addUser(q);
    const loading = addLoading();
    isLoading = true;
    send.disabled = true;
    
    try{
      const res = await fetch(VERCEL_API_BASE + '/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: q, limit: 5 })
      });
      
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }
      
      const data = await res.json();
      removeLoading();
      
      // Always show bot's message first
      if (data.message) {
        addBot(data.message);
      }
      
      // Then show products if available
      if (data.items && data.items.length > 0) {
        addProducts(data.items);
        
        // Add helpful quick replies after products
        setTimeout(() => {
          addQuickReplies([
            "🔄 הראה עוד",
            "💰 הזולים ביותר",
            "⭐ מוצרים דומים"
          ]);
        }, 300);
      }
      // Don't show "no products" message - the bot's message already handles it
    } catch(e) {
      removeLoading();
      console.error('ShopiBot Error:', e);
      addBot('הייתה בעיה זמנית בחיבור לשרת. 🔧 אנא נסה שוב בעוד רגע.');
    } finally {
      isLoading = false;
      send.disabled = false;
    }
  }

  send.addEventListener('click', () => {
    const q = input.value.trim();
    if (!q || isLoading) return;
    input.value = '';
    ask(q);
  });
  
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !isLoading) {
      send.click();
    }
  });
})();
