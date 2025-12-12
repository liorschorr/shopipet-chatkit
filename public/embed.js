(function() {
    const API_BASE = "https://shopipet-chatkit.vercel.app/api"; 
    const STORAGE_KEY = 'shopipet_thread_id';
    
    // --- הגדרות צבעים (לפי המיתוג החדש) ---
    const COLORS = {
        primary: '#E91E8C',      // מג'נטה (כותרות, כפתורים, בועות משתמש)
        secondary: '#7DD3E8',    // תכלת (בועות בוט)
        background: '#F8D7E8',   // ורוד בהיר (רקע צ'אט)
        success: '#C5E8B7',      // ירוק פסטלי (אישורים)
        textMain: '#333333',     // אפור כהה
        textWhite: '#ffffff',
        border: '#f0ceda'        // גבול עדין
    };

    // כתובת האייקון - כרגע שמתי את הלוגו. תחליף את זה לקובץ הכלב המאויר שלך כשיגיע
    const ICON_URL = "https://dev.shopipet.co.il/wp-content/uploads/2025/01/a2a41b00cd5d45e70524.png"; 

    // 1. CSS משודרג וממותג
    const style = document.createElement('style');
    style.innerHTML = `
        #shopipet-widget, #shopipet-widget * {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            box-sizing: border-box;
        }

        /* --- כפתור פתיחה (האייקון) --- */
        #shopipet-trigger {
            position: fixed; bottom: 20px; right: 20px; left: auto;
            width: 70px; height: 70px; 
            background-color: #fff; /* רקע לבן לאייקון כדי שהתמונה תבלוט */
            border: 2px solid ${COLORS.primary}; 
            border-radius: 50%; 
            box-shadow: 0 4px 15px rgba(233, 30, 140, 0.4);
            cursor: pointer; z-index: 99999; display: flex;
            align-items: center; justify-content: center;
            transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            overflow: hidden;
        }
        #shopipet-trigger img {
            width: 80%; height: 80%; object-fit: contain;
        }
        #shopipet-trigger:hover { transform: scale(1.1); }

        /* --- בועת "איך אפשר לעזור?" --- */
        #shopipet-welcome-bubble {
            position: fixed; bottom: 100px; right: 25px;
            background-color: white;
            color: ${COLORS.textMain};
            padding: 10px 15px;
            border-radius: 15px;
            border-bottom-right-radius: 2px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            font-size: 14px; font-weight: bold;
            z-index: 99998;
            cursor: pointer;
            opacity: 0; transform: translateY(10px);
            transition: opacity 0.4s, transform 0.4s;
            border: 1px solid ${COLORS.primary};
        }
        #shopipet-welcome-bubble.show { opacity: 1; transform: translateY(0); }

        /* --- חלון הצ'אט --- */
        #shopipet-widget {
            position: fixed; bottom: 100px; right: 20px; left: auto;
            width: 360px; height: 550px; max-height: 80vh;
            background: #fff; 
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.15);
            display: none; flex-direction: column; z-index: 99999;
            overflow: hidden; 
            border: 2px solid ${COLORS.primary};
        }

        /* כותרת */
        .chat-header {
            background: ${COLORS.primary}; /* מג'נטה */
            padding: 18px; color: white;
            font-weight: bold; font-size: 18px;
            display: flex; justify-content: space-between; align-items: center;
        }

        /* אזור ההודעות */
        .chat-messages {
            flex: 1; padding: 20px; overflow-y: auto;
            background-color: ${COLORS.background}; /* ורוד בהיר */
            display: flex; flex-direction: column; gap: 15px;
        }

        /* בועות הודעה */
        .msg {
            max-width: 85%; padding: 12px 16px; border-radius: 18px;
            font-size: 15px; line-height: 1.5; width: fit-content; word-wrap: break-word;
            position: relative;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        .msg.user { 
            background: ${COLORS.primary}; /* מג'נטה */
            color: ${COLORS.textWhite}; 
            align-self: flex-start; /* צד ימין */
            border-bottom-right-radius: 2px;
        }
        .msg.bot { 
            background: ${COLORS.secondary}; /* תכלת */
            color: ${COLORS.textMain}; 
            align-self: flex-end; /* צד שמאל */
            border-bottom-left-radius: 2px;
        }
        .msg.error { 
            background: #ffebee; color: #c62828; 
            align-self: center; font-size: 13px; padding: 8px 12px;
        }

        /* --- כרטיסיות מוצר --- */
        .product-card {
            background: white; 
            border: 1px solid ${COLORS.secondary};
            box-shadow: 0 4px 10px rgba(0,0,0,0.03);
            border-radius: 16px; 
            padding: 15px; margin: 10px 0; width: 100%;
            text-align: center; 
            transition: transform 0.2s;
            display: flex; flex-direction: column; align-items: center;
        }
        .product-card:hover { transform: translateY(-2px); border-color: ${COLORS.primary}; }
        
        .product-image { 
            width: 120px; height: 120px; object-fit: contain; 
            margin-bottom: 10px; cursor: pointer; 
        }
        .product-title { 
            font-size: 15px; font-weight: 700; margin: 5px 0; 
            color: ${COLORS.textMain}; text-decoration: none; line-height: 1.3;
            display: block; cursor: pointer;
        }
        .product-price { font-size: 16px; color: ${COLORS.textMain}; font-weight: 600; margin: 8px 0; }
        .sale-price { color: ${COLORS.primary}; font-weight: bold; }
        .regular-price-struck { text-decoration: line-through; font-size: 13px; color: #777; margin-left: 6px; }

        .add-to-cart-btn { 
            display: inline-block; width: 100%;
            background-color: ${COLORS.primary}; /* מג'נטה */
            color: white; text-decoration: none; 
            padding: 10px 0; border-radius: 50px; 
            font-size: 14px; font-weight: 600; 
            margin-top: 8px; transition: background 0.2s;
        }
        .add-to-cart-btn:hover { background-color: #c2185b; }

        /* חיווי הקלדה */
        .typing-indicator {
            display: flex; align-items: center; gap: 6px; 
            padding: 12px 16px; background: ${COLORS.secondary}; /* תכלת */
            border-radius: 20px; width: fit-content; 
            align-self: flex-end; margin-top: 5px;
            color: ${COLORS.textMain};
        }
        .typing-text { font-size: 12px; font-style: italic; margin-right: 5px;}
        .typing-dot { width: 6px; height: 6px; background: ${COLORS.textMain}; border-radius: 50%; animation: bounce 1.4s infinite ease-in-out; }
        .typing-dot:nth-child(1) { animation-delay: -0.32s; }
        .typing-dot:nth-child(2) { animation-delay: -0.16s; }
        @keyframes bounce { 0%, 80%, 100% { transform: scale(0); } 40% { transform: scale(1); } }

        /* אזור הקלדה */
        .chat-input-area { 
            padding: 15px; background: white; border-top: 1px solid #eee; 
            display: flex; gap: 10px; 
        }
        #shopipet-input { 
            flex: 1; padding: 12px 15px; 
            border: 2px solid #e0e0e0; border-radius: 25px; 
            outline: none; font-size: 15px; transition: border-color 0.2s;
        }
        #shopipet-input:focus { border-color: ${COLORS.primary}; }
        
        #shopipet-send { 
            background: ${COLORS.primary}; border: none; 
            width: 45px; height: 45px; border-radius: 50%; 
            cursor: pointer; display: flex; align-items: center; justify-content: center; 
            color: white; font-size: 18px; transition: transform 0.2s;
        }
        #shopipet-send:hover { transform: scale(1.05); }
        
        @media (max-width: 480px) { 
            #shopipet-widget { width: 92%; right: 4%; bottom: 90px; height: 65vh; } 
        }
    `;
    document.head.appendChild(style);

    // 2. יצירת ה-HTML
    const container = document.createElement('div');
    container.innerHTML = `
        <div id="shopipet-welcome-bubble">איך אפשר לעזור? 🐾</div>
        <div id="shopipet-trigger">
            <img src="${ICON_URL}" alt="ShopiPet Chat">
        </div>
        <div id="shopipet-widget" dir="rtl">
            <div class="chat-header">
                <span>שופיבוט</span>
                <span id="shopipet-close" style="cursor:pointer; font-size: 20px;">&times;</span>
            </div>
            <div id="shopipet-messages" class="chat-messages"></div>
            <div class="chat-input-area">
                <input type="text" id="shopipet-input" placeholder="כתוב כאן..." autocomplete="off">
                <button id="shopipet-send">➤</button>
            </div>
        </div>
    `;
    document.body.appendChild(container);

    // אלמנטים
    const trigger = document.getElementById('shopipet-trigger');
    const welcomeBubble = document.getElementById('shopipet-welcome-bubble');
    const widget = document.getElementById('shopipet-widget');
    const close = document.getElementById('shopipet-close');
    const messages = document.getElementById('shopipet-messages');
    const input = document.getElementById('shopipet-input');
    const sendBtn = document.getElementById('shopipet-send');

    // --- לוגיקת בועת "איך אפשר לעזור" ---
    // הצגה אחרי חצי שנייה
    setTimeout(() => welcomeBubble.classList.add('show'), 500);
    
    // הסרה אחרי 10 שניות
    const bubbleTimeout = setTimeout(() => {
        welcomeBubble.classList.remove('show');
        setTimeout(() => welcomeBubble.remove(), 500); // מחיקה מה-DOM אחרי האנימציה
    }, 10000);

    // הסרה בלחיצה
    welcomeBubble.onclick = () => {
        clearTimeout(bubbleTimeout);
        welcomeBubble.classList.remove('show');
        setTimeout(() => welcomeBubble.remove(), 500);
        trigger.click(); // גם פותח את הצ'אט
    };

    // פתיחה/סגירה
    trigger.onclick = () => { 
        widget.style.display = 'flex'; 
        trigger.style.display = 'none'; 
        // הסרת הבועה אם עדיין קיימת
        if(welcomeBubble) welcomeBubble.style.display = 'none';
        input.focus();
    };
    close.onclick = () => { 
        widget.style.display = 'none'; 
        trigger.style.display = 'flex'; 
    };

    function scrollToBottom() { messages.scrollTop = messages.scrollHeight; }

    // פונקציית אפקט מכונת כתיבה
    function typeWriter(text, element, speed = 15) {
        let i = 0;
        element.innerHTML = ''; 
        function type() {
            if (i < text.length) {
                element.innerHTML += text.charAt(i);
                i++;
                scrollToBottom();
                setTimeout(type, speed);
            }
        }
        type();
    }

    function addMessage(text, type) {
        const div = document.createElement('div');
        div.className = `msg ${type}`;
        
        if (type === 'bot') {
            messages.appendChild(div);
            typeWriter(text, div); 
        } else {
            div.innerText = text;
            messages.appendChild(div);
        }
        scrollToBottom();
    }

    function renderProductCards(products) {
        products.forEach(p => {
            const card = document.createElement('div');
            card.className = 'product-card';
            let priceHtml = `<div class="product-price">${p.price}</div>`;
            if (p.on_sale) {
                priceHtml = `
                    <div class="product-price">
                        <span class="sale-price">${p.sale_price}</span>
                        <span class="regular-price-struck">${p.regular_price}</span>
                    </div>`;
            }
            card.innerHTML = `
                <a href="${p.permalink}" target="_blank" style="text-decoration:none;">
                    <img src="${p.image}" class="product-image" alt="${p.name}" onerror="this.src='https://via.placeholder.com/150?text=No+Image'">
                </a>
                <a href="${p.permalink}" target="_blank" class="product-title">${p.name}</a>
                ${priceHtml}
                <a href="${p.add_to_cart_url}" target="_blank" class="add-to-cart-btn">הוסף לסל 🛒</a>
            `;
            messages.appendChild(card);
        });
        scrollToBottom();
    }

    // חיווי הקלדה
    let typingTimer = null;
    function showTypingIndicator() {
        if (document.getElementById('shopipet-typing')) return;
        const div = document.createElement('div');
        div.id = 'shopipet-typing';
        div.className = 'typing-indicator';
        div.innerHTML = `
            <span class="typing-text" id="typing-status-text">חושב...</span>
            <div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>
        `;
        messages.appendChild(div);
        scrollToBottom();

        if (typingTimer) clearTimeout(typingTimer);
        typingTimer = setTimeout(() => {
            const textEl = document.getElementById('typing-status-text');
            if (textEl) textEl.innerText = "מקליד...";
        }, 1500);
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
        
        const startTime = Date.now();
        showTypingIndicator(); 

        const storedThreadId = localStorage.getItem(STORAGE_KEY);

        try {
            const res = await fetch(`${API_BASE}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text, thread_id: storedThreadId })
            });

            const data = await res.json();
            
            // השהייה מלאכותית ל-2 שניות
            const elapsedTime = Date.now() - startTime;
            const minDisplayTime = 2000; 
            if (elapsedTime < minDisplayTime) {
                await new Promise(resolve => setTimeout(resolve, minDisplayTime - elapsedTime));
            }

            removeTypingIndicator();

            if (data.thread_id) localStorage.setItem(STORAGE_KEY, data.thread_id);

            if (data.action === 'show_products' && data.products) {
                if (data.reply) addMessage(data.reply, 'bot');
                setTimeout(() => renderProductCards(data.products), data.reply ? (data.reply.length * 15) + 200 : 0);
            } else if (data.message) {
                addMessage(data.message, 'bot');
            } else if (data.reply) {
                addMessage(data.reply, 'bot');
            } else if (data.error) {
                addMessage("שגיאה: " + data.error, 'error');
            } else {
                addMessage("לא התקבלה תשובה.", 'error');
            }

        } catch (e) {
            await new Promise(resolve => setTimeout(resolve, 1000));
            removeTypingIndicator();
            console.error(e);
            addMessage("בעיית תקשורת, נסה שוב.", 'error');
        }

        input.disabled = false;
        input.focus();
    }

    sendBtn.onclick = sendMessage;
    input.onkeypress = (e) => { if(e.key === 'Enter') sendMessage(); };

})();
