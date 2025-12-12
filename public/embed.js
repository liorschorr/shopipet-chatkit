(function() {
    const API_BASE = "https://shopipet-chatkit.vercel.app/api"; 
    const STORAGE_KEY = 'shopipet_thread_id';
    
    // --- הגדרות צבעים (לפי המיתוג החדש) ---
    const COLORS = {
        primary: '#6b2c91',      // סגול מותג (כותרות, בועות משתמש)
        secondary: '#fce7f3',    // ורוד בהיר (רקע כללי)
        accent: '#fbbf24',       // צהוב (הדגשות, אייקון)
        button: '#374151',       // אפור כהה (כפתורים)
        buttonHover: '#1f2937',  // אפור כהה יותר (במעבר עכבר)
        textBot: '#333333',
        textUser: '#ffffff',
        border: '#f3e7f1'
    };

    // 1. CSS משודרג וממותג
    const style = document.createElement('style');
    style.innerHTML = `
        /* פונט כללי */
        #shopipet-widget, #shopipet-widget * {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            box-sizing: border-box;
        }

        /* כפתור פתיחה */
        #shopipet-trigger {
            position: fixed; bottom: 20px; right: 20px; left: auto;
            width: 65px; height: 65px; 
            background-color: ${COLORS.accent}; /* צהוב */
            border: 3px solid ${COLORS.primary}; /* מסגרת סגולה */
            border-radius: 50%; 
            box-shadow: 0 4px 15px rgba(107, 44, 145, 0.3);
            cursor: pointer; z-index: 99999; display: flex;
            align-items: center; justify-content: center; font-size: 32px;
            transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        }
        #shopipet-trigger:hover { transform: scale(1.1) rotate(10deg); }

        /* חלון הצ'אט */
        #shopipet-widget {
            position: fixed; bottom: 100px; right: 20px; left: auto;
            width: 360px; height: 550px; max-height: 80vh;
            background: #fff; 
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.15);
            display: none; flex-direction: column; z-index: 99999;
            overflow: hidden; 
            border: 1px solid ${COLORS.border};
        }

        /* כותרת */
        .chat-header {
            background: ${COLORS.primary}; /* סגול */
            padding: 18px; color: white;
            font-weight: bold; font-size: 18px;
            display: flex; justify-content: space-between; align-items: center;
            border-bottom: 4px solid ${COLORS.accent}; /* פס צהוב למטה */
        }

        /* אזור ההודעות */
        .chat-messages {
            flex: 1; padding: 20px; overflow-y: auto;
            background-color: ${COLORS.secondary}; /* ורוד בהיר */
            display: flex; flex-direction: column; gap: 15px;
        }

        /* בועות הודעה */
        .msg {
            max-width: 85%; padding: 12px 16px; border-radius: 18px;
            font-size: 15px; line-height: 1.5; width: fit-content; word-wrap: break-word;
            position: relative;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }
        .msg.user { 
            background: ${COLORS.primary}; 
            color: ${COLORS.textUser}; 
            align-self: flex-start; /* ימין */
            border-bottom-right-radius: 4px;
        }
        .msg.bot { 
            background: #ffffff; 
            color: ${COLORS.textBot}; 
            align-self: flex-end; /* שמאל */
            border-bottom-left-radius: 4px;
            border: 1px solid #e5e7eb;
        }
        .msg.error { 
            background: #fee2e2; color: #991b1b; 
            align-self: center; font-size: 13px; padding: 8px 12px;
        }

        /* --- כרטיסיות מוצר (Product Cards) --- */
        .product-card {
            background: white; 
            border: 2px solid ${COLORS.border};
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            border-radius: 16px; 
            padding: 15px; 
            margin: 10px 0; 
            width: 100%;
            text-align: center; 
            transition: transform 0.2s;
            display: flex; flex-direction: column; align-items: center;
        }
        .product-card:hover { transform: translateY(-3px); box-shadow: 0 6px 15px rgba(0,0,0,0.1); }
        
        .product-image { 
            width: 120px; height: 120px; object-fit: contain; 
            margin-bottom: 10px; cursor: pointer; 
        }
        
        .product-title { 
            font-size: 15px; font-weight: 700; margin: 5px 0; 
            color: #111; text-decoration: none; line-height: 1.3;
            display: block; cursor: pointer;
        }
        .product-title:hover { color: ${COLORS.primary}; }

        .product-price { font-size: 16px; color: #444; font-weight: 600; margin: 8px 0; }
        .sale-price { color: #dc2626; font-weight: bold; }
        .regular-price-struck { text-decoration: line-through; font-size: 13px; color: #9ca3af; margin-left: 6px; }

        .add-to-cart-btn { 
            display: inline-block; width: 100%;
            background-color: ${COLORS.button}; /* אפור */
            color: white; text-decoration: none; 
            padding: 10px 0; border-radius: 50px; 
            font-size: 14px; font-weight: 600; 
            margin-top: 8px; transition: background 0.2s;
        }
        .add-to-cart-btn:hover { background-color: ${COLORS.buttonHover}; }

        /* --- אנימציית הקלדה --- */
        .typing-indicator {
            display: flex; align-items: center; gap: 6px; 
            padding: 12px 16px; background: white; border-radius: 20px;
            width: fit-content; align-self: flex-end; margin-top: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }
        .typing-dot { 
            width: 6px; height: 6px; background: #9ca3af; border-radius: 50%; 
            animation: bounce 1.4s infinite ease-in-out; 
        }
        .typing-dot:nth-child(1) { animation-delay: -0.32s; }
        .typing-dot:nth-child(2) { animation-delay: -0.16s; }
        .typing-text { font-size: 12px; color: #6b7280; margin-right: 8px; font-style: italic;}
        
        @keyframes bounce { 0%, 80%, 100% { transform: scale(0); } 40% { transform: scale(1); } }

        /* אזור הקלדה */
        .chat-input-area { 
            padding: 15px; background: white; border-top: 1px solid #f3f4f6; 
            display: flex; gap: 10px; 
        }
        #shopipet-input { 
            flex: 1; padding: 12px 15px; 
            border: 2px solid #e5e7eb; border-radius: 25px; 
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
        <div id="shopipet-trigger">🐶</div>
        <div id="shopipet-widget" dir="rtl">
            <div class="chat-header">
                <span>שופיבוט 🐾</span>
                <span id="shopipet-close" style="cursor:pointer; font-size: 20px;">&times;</span>
            </div>
            <div id="shopipet-messages" class="chat-messages"></div>
            <div class="chat-input-area">
                <input type="text" id="shopipet-input" placeholder="איך אפשר לעזור?..." autocomplete="off">
                <button id="shopipet-send">➤</button>
            </div>
        </div>
    `;
    document.body.appendChild(container);

    // אלמנטים
    const trigger = document.getElementById('shopipet-trigger');
    const widget = document.getElementById('shopipet-widget');
    const close = document.getElementById('shopipet-close');
    const messages = document.getElementById('shopipet-messages');
    const input = document.getElementById('shopipet-input');
    const sendBtn = document.getElementById('shopipet-send');

    // פתיחה/סגירה
    trigger.onclick = () => { 
        widget.style.display = 'flex'; 
        trigger.style.display = 'none'; 
        input.focus();
    };
    close.onclick = () => { 
        widget.style.display = 'none'; 
        trigger.style.display = 'flex'; 
    };

    function scrollToBottom() { messages.scrollTop = messages.scrollHeight; }

    // פונקציית אפקט מכונת כתיבה (Typewriter)
    function typeWriter(text, element, speed = 15) {
        let i = 0;
        element.innerHTML = ''; // ניקוי התחלה
        
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
            // לבוט: מתחילים ריק ומפעילים אפקט הקלדה
            messages.appendChild(div);
            typeWriter(text, div); 
        } else {
            // למשתמש: טקסט מידי
            div.innerText = text;
            messages.appendChild(div);
        }
        scrollToBottom();
    }

    // פונקציית הצגת מוצרים
    function renderProductCards(products) {
        products.forEach(p => {
            const card = document.createElement('div');
            card.className = 'product-card';
            
            // לוגיקת מחיר (מבצע או רגיל)
            let priceHtml = `<div class="product-price">${p.price}</div>`;
            if (p.on_sale) {
                priceHtml = `
                    <div class="product-price">
                        <span class="sale-price">${p.sale_price}</span>
                        <span class="regular-price-struck">${p.regular_price}</span>
                    </div>`;
            }

            // קישורים חכמים
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

    // --- ניהול חיווי הקלדה חכם ---
    let typingTimer = null;

    function showTypingIndicator() {
        if (document.getElementById('shopipet-typing')) return;
        
        const div = document.createElement('div');
        div.id = 'shopipet-typing';
        div.className = 'typing-indicator';
        div.innerHTML = `
            <span class="typing-text" id="typing-status-text">חושב...</span>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        `;
        messages.appendChild(div);
        scrollToBottom();

        // החלפת טקסט אחרי 1.5 שניות כדי להראות חיים
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

    // --- הפונקציה המרכזית (שליחה) ---
    async function sendMessage() {
        const text = input.value.trim();
        if (!text) return;

        addMessage(text, 'user'); // הודעת משתמש מיד
        input.value = '';
        input.disabled = true;
        
        // 1. התחלת שעון (Artificial Delay)
        const startTime = Date.now();
        showTypingIndicator(); // מציג "חושב..."

        const storedThreadId = localStorage.getItem(STORAGE_KEY);

        try {
            const res = await fetch(`${API_BASE}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text, thread_id: storedThreadId })
            });

            const data = await res.json();
            
            // 2. חישוב זמן המתנה מינימלי (2 שניות)
            // זה מבטיח שהחיווי לא ייעלם מהר מדי
            const elapsedTime = Date.now() - startTime;
            const minDisplayTime = 2000; 

            if (elapsedTime < minDisplayTime) {
                await new Promise(resolve => setTimeout(resolve, minDisplayTime - elapsedTime));
            }

            // 3. הסרת החיווי והצגת התשובה
            removeTypingIndicator();

            if (data.thread_id) localStorage.setItem(STORAGE_KEY, data.thread_id);

            // טיפול במוצרים או הודעה
            if (data.action === 'show_products' && data.products) {
                if (data.reply) addMessage(data.reply, 'bot'); // טקסט מקדים
                // השהייה קטנה לפני הצגת המוצרים כדי שהטקסט יוקלד קודם
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
            await new Promise(resolve => setTimeout(resolve, 1000)); // השהייה גם בשגיאה
            removeTypingIndicator();
            console.error(e);
            addMessage("בעיית תקשורת, נסה שוב.", 'error');
        }

        input.disabled = false;
        input.focus();
    }

    sendBtn.onclick = sendMessage;
    input.onkeypress = (e) => { if(e.key === 'Enter') sendMessage(); };

    // הודעת פתיחה (אופציונלי)
    // setTimeout(() => addMessage("היי! אני שופיבוט 🐶, איך אפשר לעזור?", 'bot'), 1000);

})();
