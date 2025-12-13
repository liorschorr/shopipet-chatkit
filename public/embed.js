(function() {
    const API_BASE = "https://shopipet-chatkit.vercel.app/api"; 
    const STORAGE_KEY = 'shopipet_thread_id';
    
    // --- הגדרות צבעים (לפי המיתוג) ---
    const COLORS = {
        primary: '#E91E8C',      // מג'נטה
        secondary: '#7DD3E8',    // תכלת
        background: '#F8D7E8',   // ורוד בהיר
        textMain: '#333333',     // אפור כהה
        textWhite: '#ffffff',
        border: '#f0ceda'
    };

    const ICON_URL = "https://dev.shopipet.co.il/wp-content/uploads/2025/01/a2a41b00cd5d45e70524.png";

    const style = document.createElement('style');
    style.innerHTML = `
        /* איפוס */
        #shopipet-widget, #shopipet-widget * {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            box-sizing: border-box;
        }

        /* --- כפתור פתיחה --- */
        #shopipet-trigger {
            position: fixed; bottom: 20px; right: 20px; left: auto;
            width: 70px; height: 70px; 
            background-color: #fff;
            border: 2px solid ${COLORS.primary}; 
            border-radius: 50%; 
            box-shadow: 0 4px 15px rgba(233, 30, 140, 0.4);
            cursor: pointer; z-index: 99999; display: flex;
            align-items: center; justify-content: center;
            transition: transform 0.3s ease;
        }
        #shopipet-trigger img { width: 80%; height: 80%; object-fit: contain; }
        #shopipet-trigger:hover { transform: scale(1.1); }

        /* --- בועת עזרה --- */
        #shopipet-welcome-bubble {
            position: fixed; bottom: 100px; right: 25px;
            background-color: white; color: ${COLORS.textMain};
            padding: 10px 15px; border-radius: 15px; border-bottom-right-radius: 2px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1); font-size: 14px; font-weight: bold;
            z-index: 99998; cursor: pointer; opacity: 0; transform: translateY(10px);
            transition: opacity 0.4s, transform 0.4s; border: 1px solid ${COLORS.primary};
        }
        #shopipet-welcome-bubble.show { opacity: 1; transform: translateY(0); }

        /* --- חלון הצ'אט --- */
        #shopipet-widget {
            position: fixed; bottom: 100px; right: 20px; left: auto;
            width: 360px; height: 550px; max-height: 80vh;
            background: #fff; 
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            display: none; 
            flex-direction: column; /* חובה לסידור האלמנטים */
            z-index: 99999;
            overflow: hidden; 
            border: 2px solid ${COLORS.primary};
        }

        /* כותרת */
        .chat-header {
            background: ${COLORS.primary}; padding: 15px; color: white;
            font-weight: bold; font-size: 18px;
            display: flex; justify-content: space-between; align-items: center;
            flex-shrink: 0; /* מונע מהכותרת להתכווץ כשהמקלדת עולה */
            height: 60px;
        }

        /* אזור הודעות */
        .chat-messages {
            flex-grow: 1; /* תופס את כל הגובה הפנוי */
            padding: 15px; overflow-y: auto;
            background-color: ${COLORS.background};
            display: flex; flex-direction: column; gap: 12px;
            -webkit-overflow-scrolling: touch;
        }

        /* בועות הודעה */
        .msg {
            max-width: 85%; padding: 10px 14px; border-radius: 18px;
            font-size: 15px; line-height: 1.4; word-wrap: break-word;
            text-align: right; direction: rtl;
        }
        .msg.user { 
            background: ${COLORS.primary}; color: ${COLORS.textWhite}; 
            align-self: flex-start; border-bottom-right-radius: 2px;
        }
        .msg.bot { 
            background: ${COLORS.secondary}; color: ${COLORS.textMain}; 
            align-self: flex-end; border-bottom-left-radius: 2px;
        }
        .msg.error { background: #ffebee; color: #c62828; align-self: center; font-size: 13px; text-align: center;}

        /* כרטיסיות מוצר */
        .product-card {
            background: white; border: 1px solid white; box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            border-radius: 12px; padding: 10px; margin: 5px 0; width: 100%; text-align: center;
            direction: rtl;
        }
        .product-image { width: 90px; height: 90px; object-fit: contain; margin: 0 auto; display: block; }
        .product-title { font-size: 14px; font-weight: bold; color: #333; text-decoration: none; display: block; margin: 5px 0; }
        .product-price { font-size: 14px; font-weight: bold; color: ${COLORS.primary}; }
        .old-price { text-decoration: line-through; color: #999; font-size: 12px; margin-left: 5px; }
        
        .add-cart-btn {
            background: #333; color: white; padding: 6px 0; width: 100%; display: block;
            border-radius: 20px; text-decoration: none; font-size: 13px; margin-top: 5px;
        }

        /* חיווי הקלדה */
        .typing { 
            font-size: 12px; color: #666; font-style: italic; 
            margin-right: 10px; align-self: flex-end; text-align: right;
        }

        /* --- אזור הקלדה --- */
        .chat-input-area {
            padding: 10px; background: white; border-top: 1px solid #eee;
            display: flex; gap: 10px; align-items: center;
            flex-shrink: 0; /* מונע כיווץ */
            min-height: 60px;
            /* שיפור לאייפון למטה */
            padding-bottom: env(safe-area-inset-bottom, 10px);
        }
        #shopipet-input {
            flex: 1; padding: 12px 15px;
            border: 2px solid #e0e0e0; border-radius: 25px;
            outline: none; font-size: 16px; /* מונע זום באייפון */
            direction: rtl;
        }
        #shopipet-input:focus { border-color: ${COLORS.primary}; }
        
        #shopipet-send {
            background: ${COLORS.primary}; border: none; color: white;
            width: 42px; height: 42px; border-radius: 50%; cursor: pointer;
            display: flex; align-items: center; justify-content: center; font-size: 18px;
            transform: rotate(180deg);
            transition: background 0.3s;
        }
        #shopipet-send:hover { background-color: #c2185b; }

        /* --- מובייל: התיקון הגדול --- */
        @media (max-width: 480px) {
            #shopipet-widget {
                position: fixed;
                top: 20px; /* רווח קטן מלמעלה */
                
                /* הקסם: גובה דינמי שתופס את כל המסך פחות השוליים, ומתחשב במקלדת */
                height: calc(100dvh - 40px) !important;
                /* תמיכה לאחור בדפדפנים ישנים */
                height: calc(100vh - 40px);
                
                width: 90% !important;
                left: 5%;
                right: 5%;
                bottom: auto; /* מבטל את העוגן התחתון כדי לאפשר גובה דינמי */
                
                max-height: none;
                border-radius: 15px;
                display: flex;
                flex-direction: column;
            }
            #shopipet-trigger { width: 60px; height: 60px; bottom: 15px; right: 15px; }
        }
    `;
    document.head.appendChild(style);

    // 2. יצירת HTML
    const container = document.createElement('div');
    container.innerHTML = `
        <div id="shopipet-welcome-bubble">איך אפשר לעזור? 🐾</div>
        <div id="shopipet-trigger"><img src="${ICON_URL}"></div>
        <div id="shopipet-widget" dir="rtl">
            <div class="chat-header"><span>שופיבוט</span><span id="shopipet-close" style="cursor:pointer;">&times;</span></div>
            <div id="shopipet-messages" class="chat-messages"></div>
            <div class="chat-input-area">
                <input type="text" id="shopipet-input" placeholder="כתוב כאן..." autocomplete="off">
                <button id="shopipet-send">➤</button>
            </div>
        </div>
    `;
    document.body.appendChild(container);

    const trigger = document.getElementById('shopipet-trigger');
    const widget = document.getElementById('shopipet-widget');
    const close = document.getElementById('shopipet-close');
    const bubble = document.getElementById('shopipet-welcome-bubble');
    const messages = document.getElementById('shopipet-messages');
    const input = document.getElementById('shopipet-input');
    const send = document.getElementById('shopipet-send');

    // בועה
    setTimeout(() => bubble.classList.add('show'), 1000);
    setTimeout(() => bubble.classList.remove('show'), 11000);
    bubble.onclick = () => { bubble.remove(); trigger.click(); };

    // פתיחה/סגירה
    trigger.onclick = () => { 
        widget.style.display = 'flex'; 
        trigger.style.display = 'none'; 
        bubble.remove(); 
        setTimeout(scrollToBottom, 100);
        
        // טריגר ראשוני לחישוב גובה (למקרה שהדפדפן צריך ניעור)
        if (window.innerWidth < 480 && window.visualViewport) {
            handleVisualResize();
        }
    };
    close.onclick = () => { widget.style.display = 'none'; trigger.style.display = 'flex'; };

    // גלילה חכמה
    function scrollToBottom() { 
        messages.scrollTop = messages.scrollHeight; 
    }

    // הקפצה למטה כשהמקלדת נפתחת
    input.addEventListener('focus', () => {
        setTimeout(scrollToBottom, 300);
        // וידוא שהחלון כולו נגלל לאזור הנכון
        setTimeout(() => input.scrollIntoView({behavior: "smooth", block: "center"}), 400);
    });

    // --- לוגיקה לתיקון גודל מסך במובייל (Visual Viewport API) ---
    // זה מבטיח שהווידג'ט מתכווץ פיזית כשהמקלדת עולה
    function handleVisualResize() {
        if (!widget || widget.style.display === 'none') return;
        
        // מפעיל רק במובייל
        if (window.innerWidth < 480 && window.visualViewport) {
            // משנה את גובה הוידג'ט לגובה הויזואלי הזמין פחות שוליים
            // המספר 40 מייצג את ה-margin (20 למעלה + 20 למטה)
            widget.style.height = (window.visualViewport.height - 40) + 'px';
            
            // מוודא שאנחנו רואים את הלמטה
            scrollToBottom();
        }
    }

    // האזנה לאירועי מקלדת ושינוי גודל
    if (window.visualViewport) {
        window.visualViewport.addEventListener('resize', handleVisualResize);
        window.visualViewport.addEventListener('scroll', handleVisualResize);
    }

    // הוספת הודעה
    function addMessage(text, type) {
        const div = document.createElement('div');
        div.className = `msg ${type}`;
        
        if (type === 'bot') {
            messages.appendChild(div);
            let i = 0; div.innerHTML = '';
            function typeChar() {
                if (i < text.length) {
                    div.innerHTML += text.charAt(i); i++;
                    setTimeout(typeChar, 10);
                    messages.scrollTop = messages.scrollHeight;
                }
            }
            typeChar();
        } else {
            div.innerText = text;
            messages.appendChild(div);
        }
        scrollToBottom();
    }

    // כרטיסיות
    function renderProducts(products) {
        products.forEach(p => {
            const card = document.createElement('div');
            card.className = 'product-card';
            let priceHtml = `<div class="product-price">${p.price}</div>`;
            if (p.on_sale) {
                priceHtml = `<div class="product-price">${p.sale_price} <span class="old-price">${p.regular_price}</span></div>`;
            }
            card.innerHTML = `
                <a href="${p.permalink}" target="_blank"><img src="${p.image}" class="product-image"></a>
                <a href="${p.permalink}" target="_blank" class="product-title">${p.name}</a>
                ${priceHtml}
                <a href="${p.add_to_cart_url}" target="_blank" class="add-cart-btn">הוסף לסל 🛒</a>
            `;
            messages.appendChild(card);
        });
        scrollToBottom();
    }

    function showTyping() {
        const div = document.createElement('div'); div.id='typing'; div.className='typing'; div.innerText='מקליד...';
        messages.appendChild(div); scrollToBottom();
    }
    function hideTyping() { const el=document.getElementById('typing'); if(el) el.remove(); }

    async function sendMessage() {
        const text = input.value.trim();
        if (!text) return;
        addMessage(text, 'user');
        input.value = ''; input.disabled = true; showTyping();

        try {
            const res = await fetch(`${API_BASE}/chat`, {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ message: text, thread_id: localStorage.getItem(STORAGE_KEY) })
            });
            const data = await res.json();
            hideTyping();
            if (data.thread_id) localStorage.setItem(STORAGE_KEY, data.thread_id);

            await new Promise(r => setTimeout(r, 500));

            if (data.action === 'show_products' && data.products) {
                if (data.reply) addMessage(data.reply, 'bot');
                setTimeout(() => renderProducts(data.products), (data.reply ? data.reply.length * 15 : 0) + 300);
            } else if (data.reply) {
                addMessage(data.reply, 'bot');
            } else if (data.error) {
                addMessage("שגיאה: " + data.error, 'error');
            }
        } catch (e) {
            hideTyping(); addMessage("שגיאת תקשורת.", 'error');
        }
        input.disabled = false; input.focus();
    }

    send.onclick = sendMessage;
    input.onkeypress = (e) => { if (e.key === 'Enter') sendMessage(); };
})();