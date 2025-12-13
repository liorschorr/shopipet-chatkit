(function() {
    const API_BASE = "https://shopipet-chatkit.vercel.app/api";
    const STORAGE_KEY = 'shopipet_thread_id';
    const CONVERSATION_KEY = 'shopipet_conversation';
    const WIDGET_STATE_KEY = 'shopipet_widget_state';

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

        /* SKU מוצר */
        .product-sku {
            font-size: 11px;
            color: #999;
            margin: 0 0 6px 0;
            font-family: monospace;
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

        /* בורר כמות */
        .quantity-selector {
            display: flex;
            align-items: center;
            gap: 4px;
            flex-shrink: 0;
        }
        .quantity-btn {
            background: ${COLORS.primary};
            color: white;
            width: 24px;
            height: 24px;
            border-radius: 50%;
            border: none;
            cursor: pointer;
            font-size: 16px;
            font-weight: bold;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: background 0.2s;
            padding: 0;
            line-height: 1;
        }
        .quantity-btn:hover {
            background: #c2185b;
        }
        .quantity-btn:active {
            transform: scale(0.95);
        }
        .quantity-input {
            width: 35px;
            height: 24px;
            text-align: center;
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            font-size: 13px;
            font-weight: 600;
            padding: 0;
        }
        .quantity-input:focus {
            outline: none;
            border-color: ${COLORS.primary};
        }

        /* בוחר וריאציות */
        .variation-selector {
            margin: 8px 0;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        .variation-option {
            background: white;
            border: 1.5px solid #e0e0e0;
            border-radius: 8px;
            padding: 8px 10px;
            font-size: 12px;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            justify-content: space-between;
            align-items: center;
            text-align: right;
        }
        .variation-option:hover {
            border-color: ${COLORS.primary};
            background: #fff5fb;
        }
        .variation-option.selected {
            border-color: ${COLORS.primary};
            background: ${COLORS.primary};
            color: white;
            font-weight: 600;
        }
        .variation-name {
            flex: 1;
            font-size: 12px;
        }
        .variation-price {
            font-weight: 600;
            font-size: 13px;
            color: ${COLORS.primary};
        }
        .variation-option.selected .variation-price {
            color: white;
        }
        .more-variations-btn {
            background: #f5f5f5;
            border: 1.5px dashed #ccc;
            color: #666;
            text-decoration: none;
            display: block;
            text-align: center;
            font-size: 12px;
            padding: 8px;
            border-radius: 8px;
            transition: all 0.2s;
        }
        .more-variations-btn:hover {
            background: #ececec;
            border-color: #999;
        }

        /* חיווי הקלדה */
        .typing {
            font-size: 12px; color: #666; font-style: italic;
            margin-right: 10px; align-self: flex-end; text-align: right;
        }

        /* כפתורי פעולה מהירה */
        .quick-action-buttons {
            display: flex;
            gap: 10px;
            justify-content: center;
            margin: 10px 0;
            flex-wrap: wrap;
        }
        .quick-action-btn {
            background: white;
            border: 2px solid ${COLORS.primary};
            color: ${COLORS.primary};
            padding: 10px 20px;
            border-radius: 25px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            flex: 1;
            min-width: 120px;
            text-align: center;
        }
        .quick-action-btn:hover {
            background: ${COLORS.primary};
            color: white;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(233, 30, 140, 0.3);
        }
        .quick-action-btn:active {
            transform: translateY(0);
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
                left: 50%;
                transform: translateX(-50%);
                bottom: 0;

                /* גובה: מתחיל ב-100vh ו-JS ידאג לעדכון דינמי */
                height: 100vh;
                height: 100dvh; /* Dynamic Viewport Height - תמיכה מודרנית */

                width: 90% !important;
                max-width: 500px;
                max-height: none;
                border-radius: 0; /* מסך מלא במובייל */
                /* display מוגדר ב-JS בלבד - לא כאן! */
                flex-direction: column;

                /* מבטיח שהווידג'ט יתמקם נכון בתוך ה-Visual Viewport */
                will-change: height;
            }

            /* כותרת צמודה למעלה */
            .chat-header {
                position: sticky;
                top: 0;
                z-index: 10;
                font-size: 20px; /* +2pt */
            }

            /* אזור הודעות גמיש */
            .chat-messages {
                flex: 1;
                min-height: 0; /* חשוב! מאפשר overflow בתוך flex container */
                overflow-y: auto;
                -webkit-overflow-scrolling: touch;
            }

            /* הודעות - גופן גדול יותר */
            .msg {
                font-size: 17px; /* +2pt */
            }

            /* כותרת מוצר */
            .product-title {
                font-size: 16px; /* +2pt */
            }

            /* SKU */
            .product-sku {
                font-size: 13px; /* +2pt */
            }

            /* תיאור מוצר */
            .product-description {
                font-size: 14px; /* +2pt */
            }

            /* מחיר */
            .product-price {
                font-size: 17px; /* +2pt */
            }

            .product-old-price {
                font-size: 14px; /* +2pt */
            }

            /* כפתור הוספה לסל */
            .add-cart-btn {
                font-size: 14px; /* +2pt */
                padding: 8px 18px; /* גדול יותר לנוחות */
            }

            /* כפתורי פעולה מהירה */
            .quick-action-btn {
                font-size: 16px; /* +2pt */
                padding: 12px 22px; /* גדול יותר */
            }

            /* שדה קלט */
            #shopipet-input {
                font-size: 18px; /* +2pt (גם מונע זום באייפון) */
            }

            /* וריאציות במובייל */
            .variation-option {
                font-size: 14px; /* +2pt */
                padding: 10px 12px; /* גדול יותר למגע */
            }
            .variation-name {
                font-size: 14px; /* +2pt */
            }
            .variation-price {
                font-size: 15px; /* +2pt */
            }
            .more-variations-btn {
                font-size: 14px; /* +2pt */
                padding: 10px;
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

    // שמירת שיחה ל-localStorage
    function saveConversation() {
        try {
            const conversationData = {
                html: messages.innerHTML,
                timestamp: Date.now()
            };
            localStorage.setItem(CONVERSATION_KEY, JSON.stringify(conversationData));
        } catch (e) {
            console.error('Failed to save conversation:', e);
        }
    }

    // טעינת שיחה מ-localStorage
    function loadConversation() {
        try {
            const saved = localStorage.getItem(CONVERSATION_KEY);
            if (!saved) return false;

            const conversationData = JSON.parse(saved);
            const dayInMs = 24 * 60 * 60 * 1000;

            // מחיקת שיחה אם עברו יותר מ-7 ימים
            if (Date.now() - conversationData.timestamp > 7 * dayInMs) {
                localStorage.removeItem(CONVERSATION_KEY);
                return false;
            }

            // שחזור ה-HTML של השיחה
            messages.innerHTML = conversationData.html;

            // שחזור event listeners לכפתורים (אם יש)
            restoreEventListeners();

            return true;
        } catch (e) {
            console.error('Failed to load conversation:', e);
            return false;
        }
    }

    // שחזור event listeners אחרי טעינת שיחה
    function restoreEventListeners() {
        // שחזור כפתורי פעולה מהירה
        const quickButtons = messages.querySelectorAll('.quick-action-btn');
        quickButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const action = btn.getAttribute('data-action');
                btn.parentElement.remove();
                addMessage(action, 'user');
                handleQuickAction(action);
            });
        });

        // שחזור כפתורי "הוסף לסל" בכרטיסיות מוצרים
        const addToCartButtons = messages.querySelectorAll('.add-cart-btn');
        addToCartButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const productId = btn.getAttribute('data-product-id');
                const productType = btn.getAttribute('data-product-type');
                const variationId = btn.getAttribute('data-variation-id');
                addToCart(productId, btn, productType, variationId);
            });
        });

        // שחזור בוחר וריאציות וכפתורי כמות
        const productCards = messages.querySelectorAll('.product-card');
        productCards.forEach(card => {
            const variationOptions = card.querySelectorAll('.variation-option');
            const addToCartBtn = card.querySelector('.add-cart-btn');

            if (variationOptions.length > 0 && addToCartBtn) {
                variationOptions.forEach(option => {
                    option.addEventListener('click', () => {
                        variationOptions.forEach(opt => opt.classList.remove('selected'));
                        option.classList.add('selected');
                        const variationId = option.getAttribute('data-variation-id');
                        addToCartBtn.setAttribute('data-variation-id', variationId);
                    });
                });
            }

            // שחזור כפתורי כמות
            const quantityInput = card.querySelector('.quantity-input');
            const plusBtn = card.querySelector('.quantity-plus');
            const minusBtn = card.querySelector('.quantity-minus');

            if (quantityInput && plusBtn && minusBtn) {
                plusBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    const currentVal = parseInt(quantityInput.value);
                    if (currentVal < 99) {
                        quantityInput.value = currentVal + 1;
                    }
                });

                minusBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    const currentVal = parseInt(quantityInput.value);
                    if (currentVal > 1) {
                        quantityInput.value = currentVal - 1;
                    }
                });

                quantityInput.addEventListener('input', () => {
                    let val = parseInt(quantityInput.value);
                    if (isNaN(val) || val < 1) quantityInput.value = 1;
                    if (val > 99) quantityInput.value = 99;
                });
            }
        });
    }

    // שמירת מצב הווידג'ט (פתוח/סגור)
    function saveWidgetState(isOpen) {
        try {
            localStorage.setItem(WIDGET_STATE_KEY, isOpen ? 'open' : 'closed');
        } catch (e) {
            console.error('Failed to save widget state:', e);
        }
    }

    // טעינת מצב הווידג'ט
    function loadWidgetState() {
        try {
            return localStorage.getItem(WIDGET_STATE_KEY) === 'open';
        } catch (e) {
            return false;
        }
    }

    // טיפול בפעולות מהירות עם תשובות ברירת מחדל
    function handleQuickAction(action) {
        let response = '';

        if (action === 'מוצרים') {
            response = `נהדר! אשמח לעזור למצוא בדיוק את מה שמחפשים 🐾

אפשר:
• לספר לי על חיית המחמד (כלב, חתול, ציפור ועוד)
• לחפש לפי מקט או ברקוד
• לבקש המלצה לפי גיל, גזע או צורך מיוחד
• לשאול על קטגוריה מסוימת כמו מזון, צעצועים או אביזרים

איך נתחיל? 😊`;
        } else if (action === 'בירור הזמנות') {
            response = 'בהחלט! אשמח לעזור בכל שאלה או בקשה שיש לך. אם ברצונך לבדוק את סטטוס ההזמנה שלך, אנא ספק את מספר הטלפון (מתחיל ב-05), ואני אטפל בזה עבורך. 📦';
        }

        if (response) {
            // הצגת התשובה עם אנימציית הקלדה
            setTimeout(() => {
                addMessage(response, 'bot');
            }, 500);
        }
    }

    // הצגת הודעת ברוכים הבאים עם כפתורי פעולה
    function showWelcomeMessage() {
        // בדיקה אם כבר הוצגה הודעת הברוכים הבאים
        if (messages.children.length > 0) return;

        const welcomeDiv = document.createElement('div');
        welcomeDiv.className = 'msg bot';
        welcomeDiv.innerHTML = 'נעים להכיר, שמי שופיבוט, התפקיד שלי הוא לסייע לכם למצוא את המוצרים שאתם צריכים.<br>באיזה תחום אוכל לסייע?';
        messages.appendChild(welcomeDiv);

        const buttonsDiv = document.createElement('div');
        buttonsDiv.className = 'quick-action-buttons';
        buttonsDiv.innerHTML = `
            <button class="quick-action-btn" data-action="מוצרים">מוצרים 🛍️</button>
            <button class="quick-action-btn" data-action="בירור הזמנות">בירור הזמנות 📦</button>
        `;
        messages.appendChild(buttonsDiv);

        // הוספת אירועים לכפתורים
        buttonsDiv.querySelectorAll('.quick-action-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const action = btn.getAttribute('data-action');
                // מחיקת הכפתורים
                buttonsDiv.remove();
                // הצגת הודעת משתמש
                addMessage(action, 'user');
                // הצגת תשובה ברירת מחדל בהתאם לבחירה
                handleQuickAction(action);
            });
        });

        scrollToBottom();
        saveConversation(); // שמירת הודעת הברוכים הבאים
    }

    // פתיחה/סגירה
    trigger.onclick = () => {
        widget.style.display = 'flex';
        trigger.style.display = 'none';
        bubble.remove();

        // טעינת שיחה קיימת או הצגת הודעת ברוכים הבאים
        const conversationLoaded = loadConversation();
        if (!conversationLoaded) {
            showWelcomeMessage();
        }

        // שמירת מצב פתוח
        saveWidgetState(true);

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

        // שמירת מצב סגור
        saveWidgetState(false);
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
            // שמירה על ה-transform של ה-centering
            if (vvOffsetTop > 0) {
                widget.style.top = vvOffsetTop + 'px';
            } else {
                widget.style.top = '0px';
            }
            widget.style.transform = 'translateX(-50%)';

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
                } else {
                    // שמירה אחרי שההודעה הושלמה
                    saveConversation();
                }
            }
            typeChar();
        } else {
            div.innerText = text;
            messages.appendChild(div);
            saveConversation(); // שמירה מיידית
        }
        scrollToBottom();
    }

    // כרטיסיות מוצר - עיצוב אופקי חדש
    function renderProducts(products) {
        products.forEach(p => {
            const card = document.createElement('div');
            card.className = 'product-card';

            // Check if variable product
            const isVariable = p.type === 'variable' && p.variations && p.variations.length > 0;

            // בניית SKU (אם קיים)
            const skuHtml = p.sku
                ? `<div class="product-sku">מק"ט: ${p.sku}</div>`
                : '';

            // בניית התיאור (אם קיים)
            const descriptionHtml = p.short_description
                ? `<div class="product-description">${p.short_description}</div>`
                : '';

            // Build variations selector for variable products
            let variationsHtml = '';
            if (isVariable) {
                variationsHtml = '<div class="variation-selector">';

                p.variations.forEach((variation, index) => {
                    const isSelected = index === 0; // Select first by default
                    variationsHtml += `
                        <div class="variation-option ${isSelected ? 'selected' : ''}"
                             data-variation-id="${variation.id}"
                             data-variation-price="${variation.price}">
                            <span class="variation-name">${variation.name}</span>
                            <span class="variation-price">${variation.price}</span>
                        </div>
                    `;
                });

                // "More options" button if there are more than 3 variations
                if (p.has_more_variations) {
                    variationsHtml += `
                        <a href="${p.permalink}" class="more-variations-btn">
                            עוד אפשרויות ›
                        </a>
                    `;
                }

                variationsHtml += '</div>';
            }

            // בניית HTML של המחיר (for simple products or parent price for variable)
            let priceHtml = '';
            if (!isVariable) {
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
            }

            // בניית הכרטיסייה המלאה
            card.innerHTML = `
                <div class="product-image-wrapper">
                    <a href="${p.permalink}">
                        <img src="${p.image}" alt="${p.name}" class="product-image">
                    </a>
                </div>
                <div class="product-content">
                    <div>
                        <a href="${p.permalink}" class="product-title">
                            ${p.name}
                        </a>
                        ${skuHtml}
                        ${descriptionHtml}
                        ${variationsHtml}
                    </div>
                    <div class="product-action-row">
                        ${priceHtml}
                        <div class="quantity-selector">
                            <button class="quantity-btn quantity-plus">+</button>
                            <input type="number" class="quantity-input" value="1" min="1" max="99" />
                            <button class="quantity-btn quantity-minus">-</button>
                        </div>
                        <button class="add-cart-btn"
                                data-product-id="${p.id}"
                                data-product-type="${p.type}"
                                ${isVariable ? `data-variation-id="${p.variations[0].id}"` : ''}>
                            הוסף לסל 🛒
                        </button>
                    </div>
                </div>
            `;

            // Add event listeners for variation selection
            if (isVariable) {
                const variationOptions = card.querySelectorAll('.variation-option');
                const addToCartBtn = card.querySelector('.add-cart-btn');

                variationOptions.forEach(option => {
                    option.addEventListener('click', () => {
                        // Remove selected class from all options
                        variationOptions.forEach(opt => opt.classList.remove('selected'));
                        // Add selected class to clicked option
                        option.classList.add('selected');
                        // Update button with selected variation ID
                        const variationId = option.getAttribute('data-variation-id');
                        addToCartBtn.setAttribute('data-variation-id', variationId);
                    });
                });
            }

            // Add event listener for add-to-cart button
            const addToCartBtn = card.querySelector('.add-cart-btn');
            addToCartBtn.addEventListener('click', (e) => {
                e.preventDefault();
                const productId = addToCartBtn.getAttribute('data-product-id');
                const productType = addToCartBtn.getAttribute('data-product-type');
                const variationId = addToCartBtn.getAttribute('data-variation-id');

                addToCart(productId, addToCartBtn, productType, variationId);
            });

            // Add event listeners for quantity buttons
            const quantityInput = card.querySelector('.quantity-input');
            const plusBtn = card.querySelector('.quantity-plus');
            const minusBtn = card.querySelector('.quantity-minus');

            plusBtn.addEventListener('click', (e) => {
                e.preventDefault();
                const currentVal = parseInt(quantityInput.value);
                if (currentVal < 99) {
                    quantityInput.value = currentVal + 1;
                }
            });

            minusBtn.addEventListener('click', (e) => {
                e.preventDefault();
                const currentVal = parseInt(quantityInput.value);
                if (currentVal > 1) {
                    quantityInput.value = currentVal - 1;
                }
            });

            // Prevent invalid input
            quantityInput.addEventListener('input', () => {
                let val = parseInt(quantityInput.value);
                if (isNaN(val) || val < 1) quantityInput.value = 1;
                if (val > 99) quantityInput.value = 99;
            });

            messages.appendChild(card);
        });
        scrollToBottom();
        saveConversation(); // שמירת מוצרים
    }

    // פונקציה להוספה לסל (AJAX)
    async function addToCart(productId, buttonElement, productType = 'simple', variationId = null) {
        // Prevent double-click
        if (buttonElement.disabled) return;

        const originalText = buttonElement.innerHTML;
        buttonElement.innerHTML = 'מוסיף...';
        buttonElement.disabled = true;

        try {
            // Get quantity from quantity input (if exists), default to 1
            const card = buttonElement.closest('.product-card');
            const quantityInput = card ? card.querySelector('.quantity-input') : null;
            const quantity = quantityInput ? parseInt(quantityInput.value) : 1;

            // WooCommerce AJAX Add to Cart
            const formData = new FormData();
            formData.append('quantity', quantity);

            if (productType === 'variable' && variationId) {
                // Variable product: only send variation_id and add-to-cart
                formData.append('variation_id', variationId);
                formData.append('add-to-cart', productId);  // Parent product ID
            } else {
                // Simple product: only send add-to-cart
                formData.append('add-to-cart', productId);
            }

            const response = await fetch('/?wc-ajax=add_to_cart', {
                method: 'POST',
                body: formData,
                credentials: 'same-origin'
            });

            if (!response.ok) {
                throw new Error('Network response was not ok');
            }

            const data = await response.json();

            // Log response for debugging
            console.log('Add to cart response:', data);

            // Check if WooCommerce returned an error (WooCommerce uses 'error' property for errors)
            // Success is indicated by presence of 'fragments' or no 'error' property
            if (data.error && data.error !== false) {
                console.error('WooCommerce error:', data.error);
                buttonElement.innerHTML = 'שגיאה ❌';
                setTimeout(() => {
                    buttonElement.innerHTML = originalText;
                    buttonElement.disabled = false;
                }, 2000);
            } else {
                // Success! (either has fragments or no error)
                buttonElement.innerHTML = 'נוסף! ✓';
                setTimeout(() => {
                    buttonElement.innerHTML = originalText;
                    buttonElement.disabled = false;
                }, 2000);

                // Trigger WooCommerce cart fragments refresh
                if (typeof jQuery !== 'undefined') {
                    jQuery(document.body).trigger('wc_fragment_refresh');
                    jQuery(document.body).trigger('added_to_cart', [data.fragments, data.cart_hash]);
                } else {
                    // Fallback without jQuery
                    document.body.dispatchEvent(new CustomEvent('wc_fragment_refresh'));
                }
            }
        } catch (error) {
            console.error('Add to cart error:', error);
            buttonElement.innerHTML = 'שגיאה ❌';
            setTimeout(() => {
                buttonElement.innerHTML = originalText;
                buttonElement.disabled = false;
            }, 2000);
        }
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
    input.addEventListener('keypress', (e) => { if (e.key === 'Enter') sendMessage(); });

    // --- אתחול: שחזור מצב הווידג'ט בטעינת דף ---
    (function initWidget() {
        // בדיקה אם הווידג'ט היה פתוח בדף הקודם
        const wasOpen = loadWidgetState();

        if (wasOpen) {
            // פתיחה אוטומטית של הווידג'ט
            widget.style.display = 'flex';
            trigger.style.display = 'none';

            // טעינת שיחה קיימת
            const conversationLoaded = loadConversation();
            if (!conversationLoaded) {
                showWelcomeMessage();
            }

            setTimeout(scrollToBottom, 100);

            // טריגר ראשוני לחישוב גובה (למקרה שהדפדפן צריך ניעור)
            if (window.innerWidth < 480 && window.visualViewport) {
                updateWidgetHeight();
            }
        }
    })();
})();