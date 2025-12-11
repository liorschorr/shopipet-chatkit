(function() {
    const API_BASE = "https://shopipet-chatkit.vercel.app/api"; 

    const style = document.createElement('style');
    style.innerHTML = `
        /* --- צבעים ומסגרת --- */
        #shopipet-bubble { position: fixed; bottom: 20px; right: 20px; width: 60px; height: 60px; background: #eab308; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; color: black; font-size: 30px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); z-index: 9999; }
        #shopipet-window { position: fixed; bottom: 90px; right: 20px; width: 350px; height: 500px; background: white; border-radius: 12px; box-shadow: 0 5px 20px rgba(0,0,0,0.2); display: none; flex-direction: column; z-index: 9999; overflow: hidden; font-family: sans-serif; direction: rtl; }
        
        #shopipet-header { background: #eab308; color: black; padding: 15px; font-weight: bold; font-size: 16px; display: flex; justify-content: space-between; align-items: center; }
        #shopipet-close { cursor: pointer; font-size: 20px; }
        
        #shopipet-messages { flex: 1; padding: 15px; overflow-y: auto; background: #f9f9f9; }
        #shopipet-input-area { padding: 10px; border-top: 1px solid #eee; display: flex; background: white; }
        #shopipet-input { flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 4px; outline: none; }
        #shopipet-send { margin-right: 10px; padding: 0 20px; background: #eab308; color: black; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; }
        
        /* --- בועות הודעה --- */
        .msg { margin-bottom: 12px; padding: 10px 14px; border-radius: 12px; max-width: 85%; font-size: 14px; line-height: 1.4; word-wrap: break-word; }
        .msg.user { background: #fff9c4; align-self: flex-end; margin-right: auto; border-bottom-left-radius: 2px; }
        .msg.bot { background: #fff; border: 1px solid #e5e5e5; align-self: flex-start; border-bottom-right-radius: 2px; }
        .msg.error { background: #ffebee; color: #c62828; border: 1px solid #ffcdd2; }
        
        /* --- כרטיסי מוצר --- */
        .product-card { display: flex; background: white; border: 1px solid #eee; border-radius: 8px; padding: 8px; margin-top: 8px; margin-bottom: 8px; align-items: center; text-decoration: none; color: inherit; transition: box-shadow 0.2s; }
        .product-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .product-img { width: 50px; height: 50px; object-fit: cover; border-radius: 4px; margin-left: 10px; flex-shrink: 0; }
        .product-info { flex: 1; min-width: 0; }
        .product-name { font-weight: bold; font-size: 13px; margin-bottom: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .product-price { color: #eab308; font-weight: bold; font-size: 13px; }
        .product-btn { background: #000; color: #fff; font-size: 11px; padding: 4px 8px; border-radius: 4px; margin-right: auto; }
    `;
    document.head.appendChild(style);

    // יצירת אלמנטים
    const bubble = document.createElement('div');
    bubble.id = 'shopipet-bubble';
    bubble.innerHTML = '🐾';
    
    const win = document.createElement('div');
    win.id = 'shopipet-window';
    win.innerHTML = `
        <div id="shopipet-header">
            <span>שופיבוט</span>
            <span id="shopipet-close">&times;</span>
        </div>
        <div id="shopipet-messages"></div>
        <div id="shopipet-input-area">
            <input type="text" id="shopipet-input" placeholder="שאל אותי משהו...">
            <button id="shopipet-send">שלח</button>
        </div>
    `;

    document.body.appendChild(bubble);
    document.body.appendChild(win);

    let history = [];
    
    // פתיחה/סגירה
    const toggleChat = () => {
        const isHidden = win.style.display === 'none' || win.style.display === '';
        win.style.display = isHidden ? 'flex' : 'none';
        if (isHidden) setTimeout(() => document.getElementById('shopipet-input').focus(), 100);
    };

    bubble.onclick = toggleChat;
    document.getElementById('shopipet-close').onclick = toggleChat;

    // שליחת הודעה
    async function sendMessage() {
        const input = document.getElementById('shopipet-input');
        const text = input.value.trim();
        if (!text) return;

        addMessage(text, 'user');
        input.value = '';
        input.disabled = true;

        try {
            const res = await fetch(`${API_BASE}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text, history: history })
            });

            if (!res.ok) throw new Error(`Server error: ${res.status}`);

            const data = await res.json();
            
            // 1. הצגת טקסט התשובה
            if (data.message) {
                addMessage(data.message, 'bot');
                history.push({ role: 'user', content: text });
                history.push({ role: 'assistant', content: data.message });
            } else if (data.reply) {
                 // תמיכה לאחור בפורמט הישן
                addMessage(data.reply, 'bot');
            }

            // 2. הצגת כרטיסי מוצר (אם יש)
            if (data.items && Array.isArray(data.items) && data.items.length > 0) {
                data.items.forEach(item => {
                    addProductCard(item);
                });
            }

            // טיפול בשגיאות מפורשות מהשרת
            if (data.error) {
                addMessage(`שגיאה: ${data.error}`, 'error');
            }

        } catch (e) {
            addMessage(`תקלה בתקשורת: ${e.message}`, 'error');
        }
        
        input.disabled = false;
        input.focus();
    }

    function addMessage(text, sender) {
        const div = document.createElement('div');
        div.className = `msg ${sender}`;
        // המרת ירידות שורה ל-<br>
        div.innerHTML = text.replace(/\n/g, '<br>');
        const container = document.getElementById('shopipet-messages');
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
    }

    function addProductCard(item) {
        // אם אין תמונה, נשים אייקון ברירת מחדל
        const imgUrl = item.image || 'https://placehold.co/50x50?text=Pet';
        
        const card = document.createElement('a');
        card.className = 'product-card';
        card.href = item.url;
        card.target = '_blank'; // פתיחה בלשונית חדשה
        
        card.innerHTML = `
            <img src="${imgUrl}" class="product-img" alt="${item.name}">
            <div class="product-info">
                <div class="product-name">${item.name}</div>
                <div class="product-price">${item.price} ₪</div>
            </div>
            <div class="product-btn">לרכישה</div>
        `;
        
        const container = document.getElementById('shopipet-messages');
        container.appendChild(card);
        container.scrollTop = container.scrollHeight;
    }

    document.getElementById('shopipet-send').onclick = sendMessage;
    document.getElementById('shopipet-input').onkeypress = (e) => { if (e.key === 'Enter') sendMessage(); }
})();
