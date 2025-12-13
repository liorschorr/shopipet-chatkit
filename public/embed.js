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

        /* כרטיסיות מוצר - עיצוב אופקי חדש */
        .product-card {
            background: white;
            border: 1px solid #e0e0e0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            border-radius: 12px;
            padding: 12px;
            margin: 8px 0;
            width: 100%;
            direction: rtl;
            display: flex;
            flex-direction: row-reverse; /* תמונה בצד ימין */
            gap: 12px;
            align-items: stretch;
            transition: box-shadow 0.2s;
        }
        .product-card:hover {
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }

        /* תמונת מוצר - צד ימין */
        .product-image-wrapper {
            flex-shrink: 0;
            width: 80px;
            height: 80px;
        }
        .product-image {
            width: 100%;
            height: 100%;
            object-fit: cover;
            border-radius: 8px;
            display: block;
            cursor: pointer;
            transition: transform 0.2s;
        }
        .product-image:hover {
            transform: scale(1.05);
        }

        /* אזור תוכן - צד שמאל */
        .product-content {
            flex: 1;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            min-width: 0; /* מאפשר ellipsis */
        }

        /* כותרת מוצר */
        .product-title {
            font-size: 14px;
            font-weight: bold;
            color: #333;
            text-decoration: none;
            display: block;
            margin: 0 0 4px 0;
            line-height: 1.3;
            cursor: pointer;
            transition: color 0.2s;
        }
        .product-title:hover {
            color: ${COLORS.primary};
        }

        /* תיאור מוצר */
        .product-description {
            font-size: 12px;
            color: #666;
            line-height: 1.4;
            margin: 0 0 8px 0;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        /* שורת פעולה תחתונה */
        .product-action-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 8px;
            flex-wrap: nowrap;
        }

        /* מחירים */
        .product-price-container {
            display: flex;
            align-items: center;
            gap: 6px;
            flex-shrink: 0;
        }
        .product-price {
            font-size: 15px;
            font-weight: bold;
            color: ${COLORS.primary};
            white-space: nowrap;
        }
        .product-old-price {
            font-size: 12px;
            color: #999;
            text-decoration: line-through;
            white-space: nowrap;
        }

        /* כפתור הוספה לסל */
        .add-cart-btn {
            background: ${COLORS.primary};
            color: white;
            padding: 6px 16px;
            border-radius: 20px;
            text-decoration: none;
            font-size: 12px;
            font-weight: 600;
            white-space: nowrap;
            flex-shrink: 0;
            transition: background 0.2s, transform 0.1s;
            cursor: pointer;
            border: none;
            display: inline-block;
        }
        .add-cart-btn:hover {
            background: #c2185b;
            transform: translateY(-1px);
        }
        .add-cart-btn:active {
            transform: translateY(0);
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
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;

                /* גובה: מתחיל ב-100vh ו-JS ידאג לעדכון דינמי */
                height: 100vh;
                height: 100dvh; /* Dynamic Viewport Height - תמיכה מודרנית */

                width: 100% !important;
                max-height: none;
                border-radius: 0; /* מסך מלא במובייל */
                display: flex;
                flex-direction: column;

                /* מבטיח שהווידג'ט יתמקם נכון בתוך ה-Visual Viewport */
                transform: translate3d(0, 0, 0);
                will-change: height;
            }

            /* כותרת צמודה למעלה */
            .chat-header {
                position: sticky;
                top: 0;
                z-index: 10;
            }

            /* אזור הודעות גמיש */
            .chat-messages {
                flex: 1;
                min-height: 0; /* חשוב! מאפשר overflow בתוך flex container */
                overflow-y: auto;
                -webkit-overflow-scrolling: touch;
            }

            /* אזור קלט צמוד למטה */
            .chat-input-area {
                position: sticky;
                bottom: 0;
                z-index: 10;
                background: white;
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
            updateWidgetHeight();
        }
    };
    close.onclick = () => {
        widget.style.display = 'none';
        trigger.style.display = 'flex';
        resetWidgetPosition();
    };

    // גלילה חכמה
    function scrollToBottom() { 
        messages.scrollTop = messages.scrollHeight; 
    }

    // הקפצה למטה כשהמקלדת נפתחת
    input.addEventListener('focus', () => {
        // iOS: מניעת זום אוטומטי
        if (window.innerWidth < 480) {
            // עדכון מיידי של גובה הווידג'ט
            if (window.visualViewport) {
                updateWidgetHeight();
            }

            // גלילה לתחתית הודעות
            setTimeout(scrollToBottom, 300);

            // iOS Safari fix: מניעת "bounce" ואיבוד פוקוס
            setTimeout(() => {
                input.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "nearest" });
            }, 400);
        } else {
            setTimeout(scrollToBottom, 300);
        }
    });

    // תיקון נוסף: כשהמקלדת נסגרת (blur)
    input.addEventListener('blur', () => {
        if (window.innerWidth < 480 && window.visualViewport) {
            // עדכון גובה חזרה למצב רגיל
            setTimeout(updateWidgetHeight, 100);
        }
    });

    // --- Visual Viewport API: התיקון המקצועי למקלדת וירטואלית ---
    // מטפל בהבדל בין Layout Viewport ל-Visual Viewport
    let isKeyboardOpen = false;
    let previousViewportHeight = window.visualViewport ? window.visualViewport.height : window.innerHeight;

    function updateWidgetHeight() {
        // עובד רק כשהווידג'ט פתוח ובמובייל
        if (!widget || widget.style.display === 'none' || window.innerWidth >= 480) {
            return;
        }

        if (window.visualViewport) {
            const vvHeight = window.visualViewport.height;
            const vvOffsetTop = window.visualViewport.offsetTop || 0;

            // זיהוי פתיחה/סגירה של המקלדת
            const heightDifference = Math.abs(vvHeight - previousViewportHeight);
            if (heightDifference > 100) { // סף של 100px לזיהוי מקלדת
                isKeyboardOpen = vvHeight < previousViewportHeight;
            }
            previousViewportHeight = vvHeight;

            // עדכון גובה הווידג'ט לפי ה-Visual Viewport בלבד
            widget.style.height = vvHeight + 'px';

            // iOS: תיקון למיקום כשיש offset (גלילה של הדף)
            if (vvOffsetTop > 0) {
                widget.style.top = vvOffsetTop + 'px';
            } else {
                widget.style.top = '0px';
            }

            // גלילה חכמה: רק אם המקלדת נפתחה ויש פוקוס ב-input
            if (isKeyboardOpen && document.activeElement === input) {
                requestAnimationFrame(() => {
                    scrollToBottom();
                });
            }
        }
    }

    // ניקוי מיקום כשסוגרים
    function resetWidgetPosition() {
        if (window.innerWidth < 480) {
            widget.style.height = '';
            widget.style.top = '';
            isKeyboardOpen = false;
        }
    }

    // רישום Event Listeners
    if (window.visualViewport) {
        window.visualViewport.addEventListener('resize', updateWidgetHeight);
        window.visualViewport.addEventListener('scroll', updateWidgetHeight);
    }

    // Fallback לדפדפנים ישנים
    window.addEventListener('resize', () => {
        if (!window.visualViewport && window.innerWidth < 480) {
            widget.style.height = window.innerHeight + 'px';
        }
    });

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

    // כרטיסיות מוצר - עיצוב אופקי חדש
    function renderProducts(products) {
        products.forEach(p => {
            const card = document.createElement('div');
            card.className = 'product-card';

            // בניית HTML של המחיר
            let priceHtml;
            if (p.on_sale) {
                priceHtml = `
                    <div class="product-price-container">
                        <span class="product-price">${p.sale_price}</span>
                        <span class="product-old-price">${p.regular_price}</span>
                    </div>
                `;
            } else {
                priceHtml = `
                    <div class="product-price-container">
                        <span class="product-price">${p.price}</span>
                    </div>
                `;
            }

            // בניית התיאור (אם קיים)
            const descriptionHtml = p.short_description
                ? `<div class="product-description">${p.short_description}</div>`
                : '';

            // בניית הכרטיסייה המלאה
            card.innerHTML = `
                <div class="product-image-wrapper">
                    <a href="${p.permalink}" target="_blank" rel="noopener noreferrer">
                        <img src="${p.image}" alt="${p.name}" class="product-image">
                    </a>
                </div>
                <div class="product-content">
                    <div>
                        <a href="${p.permalink}" target="_blank" rel="noopener noreferrer" class="product-title">
                            ${p.name}
                        </a>
                        ${descriptionHtml}
                    </div>
                    <div class="product-action-row">
                        ${priceHtml}
                        <a href="${p.add_to_cart_url}" rel="noopener noreferrer" class="add-cart-btn">
                            הוסף לסל 🛒
                        </a>
                    </div>
                </div>
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