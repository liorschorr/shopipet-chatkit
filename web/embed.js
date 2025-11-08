(function () {
  const VERCEL_API_BASE = 'https://shopipet-chatkit.vercel.app';

  const style = document.createElement('style');
  style.innerHTML = `
  .shopibot-bubble {
    position: fixed;
    bottom: 24px;
    right: 24px;
    width: 64px;
    height: 64px;
    border-radius: 50%;
    background: #fbda16;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    box-shadow: 0 8px 24px rgba(0,0,0,.25);
    z-index: 2147483647;
  }
  .shopibot-bubble img {
    width: 52px;
    height: 52px;
    border-radius: 50%;
  }

  .shopibot-panel {
    position: fixed;
    bottom: 100px;
    right: 24px;
    width: 380px;
    max-width: 95vw;
    height: 70vh;
    max-height: 600px;
    background: #fff;
    border-radius: 16px;
    box-shadow: 0 16px 40px rgba(0,0,0,.25);
    display: none;
    flex-direction: column;
    overflow: hidden;
    z-index: 2147483646;
  }

  .shopibot-header {
    padding: 14px;
    background: #f3e7f1;
    color: #3b2e3a;
    font-weight: 600;
    text-align: center;
    font-size: 16px;
    flex-shrink: 0;
  }

  .shopibot-body {
    flex: 1;
    overflow-y: auto;
    padding: 12px;
    background: #fafafa;
    -webkit-overflow-scrolling: touch;
  }

  .shopibot-input {
    display: flex;
    gap: 8px;
    padding: 12px;
    border-top: 1px solid #ddd;
    background: #fff;
    flex-shrink: 0;
  }
  .shopibot-input input {
    flex: 1;
    padding: 10px;
    border: 1px solid #ddd;
    border-radius: 20px;
    font-size: 15px;
  }
  .shopibot-input button {
    background: #fbda16;
    border: none;
    border-radius: 20px;
    padding: 10px 18px;
    font-weight: bold;
    cursor: pointer;
  }

  .msg {
    margin: 6px 0;
    padding: 10px 14px;
    border-radius: 18px;
    max-width: 85%;
    line-height: 1.4;
    word-wrap: break-word;
  }
  .msg.user {
    background: #e3ffc4;
    margin-left: auto;
  }
  .msg.bot {
    background: #fff;
    border: 1px solid #eee;
  }

  /* כרטיס מוצר משופר */
  .prod {
    display: flex;
    flex-direction: column;
    border: 1px solid #eee;
    padding: 12px;
    border-radius: 10px;
    margin: 8px 0;
    background: #fff;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    transition: box-shadow 0.2s;
  }
  .prod:hover {
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
  }
  
  .prod-header {
    display: flex;
    gap: 10px;
    margin-bottom: 10px;
  }
  
  .prod img {
    width: 80px;
    height: 80px;
    object-fit: cover;
    border-radius: 8px;
    flex-shrink: 0;
  }
  
  .prod-info {
    flex: 1;
    min-width: 0;
  }
  
  .prod-name {
    font-size: 15px;
    font-weight: 600;
    color: #333;
    margin-bottom: 4px;
    line-height: 1.3;
  }
  
  .prod-brand {
    font-size: 12px;
    color: #666;
    margin-bottom: 4px;
  }
  
  .prod-desc {
    font-size: 13px;
    color: #555;
    line-height: 1.4;
    margin-bottom: 8px;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  
  .prod-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
  }
  
  .prod-price {
    font-size: 18px;
    font-weight: 700;
    color: #2c7a3f;
  }
  
  .prod-btn {
    background: #fbda16;
    border: none;
    border-radius: 20px;
    padding: 8px 16px;
    font-weight: 600;
    font-size: 14px;
    cursor: pointer;
    transition: background 0.2s;
    white-space: nowrap;
  }
  .prod-btn:hover {
    background: #e5c614;
  }
  .prod-btn:active {
    transform: scale(0.98);
  }

  /* תיקון מלא למובייל */
  @media (max-width: 600px) {
    .shopibot-panel {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      width: 100%;
      height: 100%;
      display: flex;
      flex-direction: column;
      border-radius: 0;
      background: #fff;
      z-index: 2147483646;
    }

    .shopibot-header {
      position: sticky;
      top: 0;
      z-index: 2;
    }

    .shopibot-body {
      flex: 1;
      overflow-y: auto;
      -webkit-overflow-scrolling: touch;
    }

    .shopibot-input {
      position: sticky;
      bottom: 0;
      z-index: 2;
      background: #fff;
    }
    
    .prod img {
      width: 70px;
      height: 70px;
    }
    
    .prod-name {
      font-size: 14px;
    }
    
    .prod-desc {
      font-size: 12px;
    }
  }
  `;
  document.head.appendChild(style);

  // bubble
  const bubble = document.createElement('div');
  bubble.className = 'shopibot-bubble';
  bubble.innerHTML = `<img src="https://www.shopipet.co.il/wp-content/uploads/2025/10/shopibot-logo.png" alt="שופיבוט" />`;

  // panel
  const panel = document.createElement('div');
  panel.className = 'shopibot-panel';
  panel.innerHTML = `
    <div class="shopibot-header">שופיבוט • עזרה לבעלי חיים</div>
    <div class="shopibot-body" id="shopibot-body"></div>
    <div class="shopibot-input">
      <input id="shopibot-input" placeholder="מה אתה מחפש היום?" />
      <button id="shopibot-send">שלח</button>
    </div>
  `;
  document.body.appendChild(bubble);
  document.body.appendChild(panel);

  function togglePanel(open) {
    panel.style.display = open ? 'flex' : 'none';
  }

  bubble.addEventListener('click', () => {
    const isOpen = panel.style.display === 'flex';
    togglePanel(!isOpen);
    if (!isOpen) showWelcome();
  });

  const body = panel.querySelector('#shopibot-body');
  const input = panel.querySelector('#shopibot-input');
  const send = panel.querySelector('#shopibot-send');

  function addUser(text) {
    const el = document.createElement('div');
    el.className = 'msg user';
    el.textContent = text;
    body.appendChild(el);
    body.scrollTop = body.scrollHeight;
  }

  function addBot(text) {
    const el = document.createElement('div');
    el.className = 'msg bot';
    el.textContent = text;
    body.appendChild(el);
    body.scrollTop = body.scrollHeight;
  }

  function addProducts(items) {
    items.forEach(p => {
      const card = document.createElement('div');
      card.className = 'prod';
      
      // בניית URL נכון למוצר
      const productUrl = p.url || `https://dev.shopipet.co.il/?s=${encodeURIComponent(p.name)}`;
      
      card.innerHTML = `
        <div class="prod-header">
          <img src="${p.image || ''}" alt="${p.name || ''}" onerror="this.src='https://via.placeholder.com/80?text=No+Image'" />
          <div class="prod-info">
            <div class="prod-name">${p.name || ''}</div>
            ${p.brand ? `<div class="prod-brand">${p.brand}</div>` : ''}
          </div>
        </div>
        <div class="prod-desc">${p.description || p.short_description || ''}</div>
        <div class="prod-footer">
          <div class="prod-price">${p.price ? '₪' + p.price : 'מחיר לא זמין'}</div>
          <button class="prod-btn" data-url="${productUrl}">הוספה לסל 🛒</button>
        </div>
      `;
      
      // כפתור הוספה לסל - פותח את דף המוצר בטאב חדש
      const btn = card.querySelector('.prod-btn');
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        window.open(productUrl, '_blank');
      });
      
      body.appendChild(card);
    });
    body.scrollTop = body.scrollHeight;
  }

  function showWelcome() {
    body.innerHTML = '';
    addBot('שלום! אני שופיבוט 🐶 איך אפשר לעזור היום?');
  }

  async function ask(q) {
    addUser(q);
    addBot('מחפש בשבילך...');
    try {
      const res = await fetch(VERCEL_API_BASE + '/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: q, limit: 5 })
      });
      const data = await res.json();
      body.lastChild.remove(); // remove "מחפש בשבילך..."
      
      // הצג את התשובה מ-OpenAI
      if (data.message) {
        addBot(data.message);
      }
      
      // הצג מוצרים אם יש
      if (data.items && data.items.length > 0) {
        addProducts(data.items);
      } else if (!data.message || data.message.includes('לא מצאתי')) {
        addBot('לא מצאתי מוצרים מתאימים 😔 נסה לנסח את החיפוש אחרת או שאל אותי משהו נוסף!');
      }
    } catch (err) {
      console.error('Error:', err);
      body.lastChild.remove();
      addBot('הייתה בעיה זמנית. נסה שוב מאוחר יותר.');
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

  // גלילה אוטומטית כמו בוואטסאפ
  input.addEventListener('focus', () => {
    setTimeout(() => {
      body.scrollTop = body.scrollHeight;
    }, 300);
  });
  input.addEventListener('blur', () => {
    setTimeout(() => {
      body.scrollTop = body.scrollHeight;
    }, 300);
  });
})();
