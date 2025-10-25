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
    transition: all .3s ease;
  }

  .shopibot-header {
    padding: 14px;
    background: #fbda16;
    color: #222;
    font-weight: 600;
    text-align: center;
    font-size: 16px;
  }

  .shopibot-body {
    flex: 1;
    overflow-y: auto;
    padding: 12px;
    background: #f7f7f7;
  }

  .shopibot-input {
    display: flex;
    gap: 8px;
    padding: 12px;
    border-top: 1px solid #ddd;
    background: #fff;
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

  @media (max-width: 600px) {
    .shopibot-panel {
      right: 0;
      left: 0;
      bottom: 0;
      width: 100%;
      height: 100%;
      max-height: none;
      border-radius: 0;
    }
    .shopibot-bubble {
      bottom: 20px;
      right: 20px;
      width: 56px;
      height: 56px;
    }
    .shopibot-bubble img {
      width: 44px;
      height: 44px;
    }
  }
  `;
  document.head.appendChild(style);

  // bubble
  const bubble = document.createElement('div');
  bubble.className = 'shopibot-bubble';
  bubble.innerHTML = `<img src="https://www.shopipet.co.il/wp-content/uploads/2025/10/shopibot-logo.png" alt="ShopiBot" />`;

  // panel
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

  function togglePanel(open) {
    panel.style.display = open ? 'flex' : 'none';
  }

  bubble.addEventListener('click', () => {
    const isOpen = panel.style.display === 'flex';
    togglePanel(!isOpen);
    if (!isOpen) addBot("שלום! איך אפשר לעזור? ספר לי על החיה שלך ומה אתה מחפש 🐾");
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
      addBot(data.message || 'הנה מה שמצאתי');
    } catch {
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

  // fix for mobile keyboard
  window.addEventListener('resize', () => {
    if (window.innerHeight < 500) {
      panel.style.height = '85vh';
    } else {
      panel.style.height = '70vh';
    }
  });
})();
