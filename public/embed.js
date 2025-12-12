(function() {
    const API_BASE = "https://shopipet-chatkit.vercel.app/api"; 
    const STORAGE_KEY = 'shopipet_thread_id';
    let typingTimer = null; // משתנה לשמירת הטיימר של החלפת הטקסט

    // 1. הוספת ה-CSS המעוצב (כולל תיקון לימין)
    const style = document.createElement('style');
    style.innerHTML = `
        /* --- כפתור פתיחה (צד ימין) --- */
        #shopipet-trigger {
            position: fixed;
            bottom: 20px;
            right: 20px; /* תוקן לימין */
            left: auto;  /* ביטול שמאל */
            width: 60px;
            height: 60px;
            background-color: #eab308;
            border-radius: 50%;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            cursor: pointer;
            z-index: 99999;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 30px;
            transition: transform 0.2s;
        }
        #shopipet-trigger:hover { transform: scale(1.1); }

        /* --- חלון הצ'אט (צד ימין) --- */
        #shopipet-widget {
            position: fixed;
            bottom: 90px;
            right: 20px; /* תוקן לימין */
            left: auto;  /* ביטול שמאל */
            width: 350px;
            height: 500px;
            max-height: 80vh; /* התאמה למסכים קטנים */
            background: white;
            border-radius: 12px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.2);
            display: none;
            flex-direction: column;
            z-index: 99999;
            overflow: hidden;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            border: 1px solid #f0f0f0;
        }

        /* כותרת */
        .chat-header {
            background: #eab308;
            padding: 15px;
            color: black;
            font-weight: bold;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        /* אזור ההודעות */
        .chat-messages {
            flex: 1;
            padding: 15px;
            overflow-y: auto;
            background: #fafafa;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        /* בועות הודעה */
        .msg {
            max-width: 80%;
            padding: 10px 14px;
            border-radius: 12px;
            font-size: 14px;
            line-height: 1.4;
            width: fit-content;
            word-wrap: break-word;
        }
        .msg.user {
            background: #eab308;
            color: black;
            align-self: flex-start; /* צד ימין בעברית */
            border-bottom-right-radius: 2px;
        }
        .msg.bot {
            background: #ffffff;
            border: 1px solid #e5e5e5;
            color: #333;
            align-self: flex-end; /* צד שמאל */
            border-bottom-left-radius: 2px;
        }
        .msg.error { background: #fee2e2; color: #991b1b; align-self: center; text-align: center; }

        /* --- סטטוס הקלדה --- */
        .typing-container {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 5px 10px;
            font-size: 12px;
            color: #666;
            background: #f5f5f5;
            border-radius: 20px;
            width: fit-content;
            align-self: flex-end;
            margin-top: 5px;
        }
        .typing-text { font-style: italic; }
        
        .typing-dots { display: flex; gap: 3px; }
        .typing-dot { width: 5px; height: 5px; background: #888; border-radius: 50%; animation: bounce 1.4s infinite ease-in-out; }
        .typing-dot:nth-child(1) { animation-delay: -0.32s; }
        .typing-dot:nth-child(2) { animation-delay: -0.16s; }
        @keyframes bounce { 0%, 80%, 100% { transform: scale(0); } 40% { transform: scale(1); } }

        /* --- כרטיסיות מוצר --- */
        .product-card {
            background: white;
            border: 5px solid #f3e7f1;
            box-shadow: 0px 6px 17px 0px rgba(0, 0, 0, 0.08);
            border-radius: 12px;
            padding: 12px;
            margin: 8px 0;
            width: 100%;
            box-sizing: border-box;
            text-align: center;
            transition: transform 0.2s;
        }
        .product-card:hover { transform: translateY(-2px); }
        .product-image { width: 100%; height: 140px; object-fit: contain; margin-bottom: 8px; cursor: pointer; }
        .product-title { font-size: 14px; font-weight: bold; margin: 5px 0; color: #333; text-decoration: none; display: block; }
        .product-price { font-size: 15px; color: #555; font-weight: 600; }
        .sale-price { color: #d32f2f; }
        .regular-price-struck { text-decoration: line-through; font-size: 12px; color: #999; margin-left: 5px; }
        .add-to-cart-btn { display: block; background-color: #000; color: #fff; text-decoration: none; padding: 8px 0; border-radius: 50px; font-size: 13px; font-weight: bold; margin-top: 10px; }

        /* אזור הקלדה */
        .chat-input-area {
            padding: 10px;
            background: white;
            border-top: 1px solid #f0f0f0;
            display: flex;
            gap: 8px;
        }
        #shopipet-input { flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 20px; outline: none; }
        #shopipet-send { background: #eab308; border: none; width: 40px; height: 40px; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; }
        
        /* התאמה למובייל */
        @media (max-width: 480px) {
            #shopipet-widget { width: 90%; right: 5%; bottom: 85px; height: 60vh; }
        }
    `;
    document.head.appendChild(style);

    // 2. יצירת ה-HTML
    const container = document.createElement('div');
    container.innerHTML = `
        <div id="shopipet-trigger">🐾</div>
        <div id="shopipet-widget" dir="rtl">
            <div class="chat-header">
                <span>שופיבוט 🐶</span>
                <span id="shopipet-close" style="cursor:pointer;">✖</span>
            </div>
            <div id="shopipet-messages" class="chat-messages"></div>
            <div class="chat-input-area">
                <input type="text" id="shopipet-input" placeholder="שאל אותי על מוצרים...">
                <button id="shopipet-send">➤</button>
            </div>
        </div>
    `;
    document.body.appendChild(container);

    const trigger = document.getElementById('shopipet-trigger');
    const widget = document.getElementById('shopipet-widget');
    const close = document.getElementById('shopipet-close');
    const messages = document.getElementById('shopipet-messages');
    const input = document.getElementById('shopipet-input');
    const sendBtn = document.getElementById('shopipet-send');

    trigger.onclick = () => { widget.style.display = 'flex'; trigger.style.display = 'none'; };
    close.onclick = () => { widget.style.display = 'none'; trigger.style.display = 'flex'; };

    function scrollToBottom() { messages.scrollTop = messages.scrollHeight; }

    function addMessage(text, type) {
        const div = document.createElement('div');
        div.className = `msg ${type}`;
        div.innerText = text;
        messages.appendChild(div);
        scrollToBottom();
    }

    function renderProductCards(products) {
        products.forEach(p => {
            const card = document.createElement('div');
            card.className = 'product-card';
            let priceHtml = `<div class="product-price">${p.price}</div>`;
            if (p.on_sale) {
                priceHtml = `<div class="product-price"><span class="sale-price">${p.sale_price}</span> <span class="regular-price-struck">${p.regular_price}</span></div>`;
            }
            card.innerHTML = `
                <a href="${p.permalink}" target="_blank"><img src="${p.image}" class="product-image"></a>
                <a href="${p.permalink}" target="_blank" class="product-title">${p.name}</a>
                ${priceHtml}
                <a href="${p.add_to_cart_url}" target="_blank" class="add-to-cart-btn">הוסף לסל 🛒</a>
            `;
            messages.appendChild(card);
        });
        scrollToBottom();
    }

    // --- לוגיקה משופרת לחיווי הקלדה ---
    function showTypingIndicator() {
        if (document.getElementById('shopipet-typing')) return;

        const div = document.createElement('div');
        div.id = 'shopipet-typing';
        div.className = 'typing-container';
        div.innerHTML = `
            <div class="typing-dots"><div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div></div>
            <span class="typing-text" id="shopipet-typing-text">חושב על תשובה...</span>
        `;
        messages.appendChild(div);
        scrollToBottom();

        // החלפת טקסט אחרי 4 שניות
        if (typingTimer) clearTimeout(typingTimer);
        typingTimer = setTimeout(() => {
            const textEl = document.getElementById('shopipet-typing-text');
            if (textEl) textEl.innerText = "מקליד...";
        }, 4000);
    }

    function removeTypingIndicator() {
        if (typingTimer) clearTimeout(typingTimer);
        const el = document.getElementById('shopipet-typing');
        if (el) el.remove();
    }

    async function sendMessage() {
        const text = input.value.trim();
        if (!text) return;

        addMessage(text, 'user');
        input.value = '';
        input.disabled = true;
        
        // הצגת החיווי מיד
        showTypingIndicator();

        const storedThreadId = localStorage.getItem(STORAGE_KEY);

        try {
            const res = await fetch(`${API_BASE}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text, thread_id: storedThreadId })
            });

            // לא מסירים את החיווי עד שהתשובה ממש הגיעה
            removeTypingIndicator();

            if (!res.ok) throw new Error("שגיאת שרת");
            const data = await res.json();

            if (data.thread_id) localStorage.setItem(STORAGE_KEY, data.thread_id);

            // טיפול במוצרים או הודעה
            if (data.action === 'show_products' && data.products) {
                if (data.reply) addMessage(data.reply, 'bot');
                renderProductCards(data.products);
            } else if (data.message) {
                addMessage(data.message, 'bot');
            } else if (data.reply) {
                addMessage(data.reply, 'bot');
            } else if (data.error) {
                addMessage("שגיאה: " + data.error, 'error');
            } else {
                addMessage("לא התקבלה תשובה ברורה.", 'error');
            }

        } catch (e) {
            removeTypingIndicator();
            console.error(e);
            addMessage("הבוט מתעכב או שיש בעיית תקשורת. נסה שוב.", 'error');
        }

        input.disabled = false;
        input.focus();
    }

    sendBtn.onclick = sendMessage;
    input.onkeypress = (e) => { if(e.key === 'Enter') sendMessage(); };

})();
