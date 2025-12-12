(function() {
    const API_BASE = "https://shopipet-chatkit.vercel.app/api"; 
    const STORAGE_KEY = 'shopipet_thread_id';
    
    // --- פלטת הצבעים החדשה ---
    const COLORS = {
        primary: '#E91E8C',      // מג'נטה (כותרת, כפתורים, בועות משתמש)
        secondary: '#7DD3E8',    // תכלת (בועות בוט)
        bg: '#F8D7E8',           // ורוד בהיר (רקע)
        success: '#C5E8B7',      // ירוק (לא בשימוש כרגע אבל קיים)
        text: '#333333',         // אפור כהה
        white: '#ffffff'
    };

    // אייקון הכלב (זמני - החלף כשתהיה לך תמונה)
    const ICON_URL = "https://dev.shopipet.co.il/wp-content/uploads/2025/01/a2a41b00cd5d45e70524.png";

    const style = document.createElement('style');
    style.innerHTML = `
        /* כללי */
        #shopipet-widget * { box-sizing: border-box; font-family: 'Segoe UI', sans-serif; }

        /* כפתור פתיחה */
        #shopipet-trigger {
            position: fixed; bottom: 20px; right: 20px;
            width: 70px; height: 70px;
            background: white; border: 2px solid ${COLORS.primary}; border-radius: 50%;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2); cursor: pointer; z-index: 99999;
            display: flex; align-items: center; justify-content: center; overflow: hidden;
        }
        #shopipet-trigger img { width: 80%; height: auto; }

        /* בועת עזרה */
        #shopipet-bubble {
            position: fixed; bottom: 100px; right: 20px;
            background: white; color: ${COLORS.text};
            padding: 10px 15px; border-radius: 15px; border-bottom-right-radius: 2px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1); font-weight: bold; font-size: 14px;
            z-index: 99998; opacity: 0; transform: translateY(10px); transition: all 0.4s;
            border: 1px solid ${COLORS.primary}; cursor: pointer;
        }
        #shopipet-bubble.show { opacity: 1; transform: translateY(0); }

        /* חלון הצ'אט */
        #shopipet-widget {
            position: fixed; bottom: 100px; right: 20px;
            width: 360px; height: 550px; max-height: 80vh;
            background: white; border-radius: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            display: none; flex-direction: column; z-index: 99999; overflow: hidden;
            border: 2px solid ${COLORS.primary};
        }

        /* כותרת */
        .chat-header {
            background: ${COLORS.primary}; color: white; padding: 15px;
            font-weight: bold; font-size: 18px;
            display: flex; justify-content: space-between; align-items: center;
        }

        /* אזור הודעות */
        .chat-messages {
            flex: 1; padding: 15px; overflow-y: auto;
            background: ${COLORS.bg}; display: flex; flex-direction: column; gap: 10px;
        }

        /* הודעות */
        .msg {
            max-width: 85%; padding: 10px 14px; border-radius: 18px; font-size: 15px; line-height: 1.4;
            position: relative; box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        }
        .msg.user {
            background: ${COLORS.primary}; color: white;
            align-self: flex-start; border-bottom-right-radius: 2px;
        }
        .msg.bot {
            background: ${COLORS.secondary}; color: ${COLORS.text};
            align-self: flex-end; border-bottom-left-radius: 2px;
        }
        .msg.error { background: #ffebee; color: #c62828; align-self: center; font-size: 13px; }

        /* כרטיסיות מוצר */
        .product-card {
            background: white; border-radius: 15px; padding: 10px; margin-top: 5px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1); text-align: center; width: 100%;
            border: 1px solid #eee;
        }
        .product-image { width: 100px; height: 100px; object-fit: contain; margin: 0 auto 5px; display: block; }
        .product-title { font-size: 14px; font-weight: bold; color: ${COLORS.text}; display: block; text-decoration: none; margin-bottom: 5px; }
        .product-price { font-size: 15px; font-weight: bold; color: ${COLORS.primary}; }
        .old-price { text-decoration: line-through; color: #999; font-size: 12px; margin-left: 5px; }
        
        .add-cart-btn {
            background: ${COLORS.text}; color: white; /* כפתור אפור כהה */
            padding: 8px 0; width: 100%; display: block; border-radius: 20px;
            text-decoration: none; font-size: 13px; font-weight: bold; margin-top: 8px;
        }
        .add-cart-btn:hover { opacity: 0.9; }

        /* הקלדה */
        .typing { font-size: 12px; color: #666; font-style: italic; align-self: flex-end; margin-right: 10px; }

        /* אזור קלט */
        .input-area { padding: 10px; background: white; display: flex; gap: 8px; border-top: 1px solid #eee; }
        #shopipet-input { flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 20px; outline: none; }
        #shopipet-send {
            background: ${COLORS.primary}; border: none; color: white;
            width: 40px; height: 40px; border-radius: 50%; cursor: pointer;
            display: flex; align-items: center; justify-content: center; font-size: 18px;
        }
    `;
    document.head.appendChild(style);

    // יצירת ה-HTML
    const container = document.createElement('div');
    container.innerHTML = `
        <div id="shopipet-bubble">איך אפשר לעזור? 🐾</div>
        <div id="shopipet-trigger"><img src="${ICON_URL}"></div>
        <div id="shopipet-widget" dir="rtl">
            <div class="chat-header"><span>שופיבוט</span><span id="shopipet-close" style="cursor:pointer;">&times;</span></div>
            <div id="shopipet-messages" class="chat-messages"></div>
            <div class="input-area">
                <input type="text" id="shopipet-input" placeholder="כתוב כאן..." autocomplete="off">
                <button id="shopipet-send">➤</button>
            </div>
        </div>
    `;
    document.body.appendChild(container);

    const trigger = document.getElementById('shopipet-trigger');
    const widget = document.getElementById('shopipet-widget');
    const close = document.getElementById('shopipet-close');
    const bubble = document.getElementById('shopipet-bubble');
    const messages = document.getElementById('shopipet-messages');
    const input = document.getElementById('shopipet-input');
    const send = document.getElementById('shopipet-send');

    // לוגיקת בועה (10 שניות)
    setTimeout(() => bubble.classList.add('show'), 1000);
    setTimeout(() => bubble.classList.remove('show'), 11000);
    bubble.onclick = () => { bubble.remove(); trigger.click(); };

    // פתיחה/סגירה
    trigger.onclick = () => { widget.style.display = 'flex'; trigger.style.display = 'none'; bubble.remove(); };
    close.onclick = () => { widget.style.display = 'none'; trigger.style.display = 'flex'; };

    // הוספת הודעה
    function addMessage(text, type) {
        const div = document.createElement('div');
        div.className = `msg ${type}`;
        
        if (type === 'bot') {
            messages.appendChild(div);
            // אפקט הקלדה
            let i = 0;
            div.innerHTML = '';
            function typeChar() {
                if (i < text.length) {
                    div.innerHTML += text.charAt(i);
                    i++;
                    setTimeout(typeChar, 15);
                    messages.scrollTop = messages.scrollHeight;
                }
            }
            typeChar();
        } else {
            div.innerText = text;
            messages.appendChild(div);
        }
        messages.scrollTop = messages.scrollHeight;
    }

    // הצגת כרטיסיות מוצר
    function renderProducts(products) {
        products.forEach(p => {
            const card = document.createElement('div');
            card.className = 'product-card';
            
            let priceHtml = `<div class="product-price">${p.price}</div>`;
            if (p.on_sale) {
                priceHtml = `<div class="product-price">${p.sale_price} <span class="old-price">${p.regular_price}</span></div>`;
            }

            card.innerHTML = `
                <a href="${p.permalink}" target="_blank">
                    <img src="${p.image}" class="product-image" alt="${p.name}">
                </a>
                <a href="${p.permalink}" target="_blank" class="product-title">${p.name}</a>
                ${priceHtml}
                <a href="${p.add_to_cart_url}" target="_blank" class="add-cart-btn">הוסף לסל 🛒</a>
            `;
            messages.appendChild(card);
        });
        messages.scrollTop = messages.scrollHeight;
    }

    // חיווי הקלדה
    function showTyping() {
        const div = document.createElement('div');
        div.id = 'typing-indicator';
        div.className = 'typing';
        div.innerText = 'מקליד...';
        messages.appendChild(div);
        messages.scrollTop = messages.scrollHeight;
    }
    function hideTyping() {
        const el = document.getElementById('typing-indicator');
        if (el) el.remove();
    }

    // שליחה
    async function sendMessage() {
        const text = input.value.trim();
        if (!text) return;

        addMessage(text, 'user');
        input.value = '';
        input.disabled = true;
        showTyping();

        try {
            const res = await fetch(`${API_BASE}/chat`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ message: text, thread_id: localStorage.getItem(STORAGE_KEY) })
            });
            const data = await res.json();
            hideTyping();

            if (data.thread_id) localStorage.setItem(STORAGE_KEY, data.thread_id);

            // אם חזרו מוצרים - הצג אותם
            if (data.action === 'show_products' && data.products) {
                if (data.reply) addMessage(data.reply, 'bot');
                setTimeout(() => renderProducts(data.products), 1000); // השהייה קטנה
            } else if (data.reply) {
                addMessage(data.reply, 'bot');
            } else if (data.error) {
                addMessage("שגיאה: " + data.error, 'error');
            }

        } catch (e) {
            hideTyping();
            addMessage("שגיאת תקשורת, נסה שוב.", 'error');
        }
        input.disabled = false;
        input.focus();
    }

    send.onclick = sendMessage;
    input.onkeypress = (e) => { if (e.key === 'Enter') sendMessage(); };

})();
