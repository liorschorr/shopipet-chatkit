(function() {
    // ⚠️ חשוב: וודא שזו הכתובת הראשית והנכונה של הפרויקט שלך ב-Vercel
    const API_BASE = "https://shopipet-chatkit.vercel.app/api"; 
    const STORAGE_KEY = 'shopibot_thread_id'; // מפתח לשמירת השיחה בדפדפן

    const style = document.createElement('style');
    style.innerHTML = `
        /* --- בסיס וצבעים --- */
        #shopipet-bubble { 
            position: fixed; bottom: 20px; right: 20px; width: 60px; height: 60px; 
            background: #eab308; border-radius: 50%; cursor: pointer; 
            display: flex; align-items: center; justify-content: center; 
            color: black; font-size: 30px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); 
            z-index: 2147483647;
            transition: transform 0.2s;
        }
        #shopipet-bubble:active { transform: scale(0.9); }
        
        #shopipet-window { 
            position: fixed; bottom: 90px; right: 20px; width: 350px; height: 500px; 
            background: white; border-radius: 12px; box-shadow: 0 5px 20px rgba(0,0,0,0.2); 
            display: none; flex-direction: column; 
            z-index: 2147483647; overflow: hidden; 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; 
            direction: rtl; 
        }

        /* --- כותרת דביקה --- */
        #shopipet-header { 
            background: #eab308; color: black; padding: 15px; font-weight: bold; font-size: 18px; 
            display: flex; justify-content: space-between; align-items: center; 
            flex-shrink: 0; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        #shopipet-close { cursor: pointer; font-size: 24px; padding: 0 5px; }
        
        /* --- אזור הודעות נגלל --- */
        #shopipet-messages { 
            flex: 1; 
            padding: 15px; overflow-y: auto; background: #f9f9f9; 
            -webkit-overflow-scrolling: touch; 
        }

        /* --- אזור הקלדה דביק למטה --- */
        #shopipet-input-area { 
            padding: 10px; border-top: 1px solid #eee; display: flex; background: white; 
            flex-shrink: 0; 
            align-items: center;
            /* התאמה לאייפון - אזור בטוח למטה */
            padding-bottom: env(safe-area-inset-bottom, 10px);
        }
        
        #shopipet-input { 
            flex: 1; padding: 12px; border: 1px solid #ddd; border-radius: 20px; outline: none; 
            font-size: 16px; /* מונע זום באייפון */
        }
        
        #shopipet-send { 
            margin-right: 10px; padding: 8px 15px; background: #eab308; color: black; 
            border: none; border-radius: 20px; cursor: pointer; font-weight: bold; font-size: 14px;
        }

        /* --- בועות הודעה --- */
        .msg { margin-bottom: 12px; padding: 10px 14px; border-radius: 12px; max-width: 85%; font-size: 15px; line-height: 1.4; word-wrap: break-word; }
        .msg.user { background: #fff9c4; align-self: flex-end; margin-right: auto; border-bottom-left-radius: 2px; }
        .msg.bot { background: #fff; border: 1px solid #e5e5e5; align-self: flex-start; border-bottom-right-radius: 2px; }
        .msg.error { background: #ffebee; color: #c62828; border: 1px solid #ffcdd2; direction: ltr; text-align: left; }

        /* --- כרטיסי מוצר --- */
        .product-card { display: flex; background: white; border: 1px solid #eee; border-radius: 8px; padding: 8px; margin-top: 8px; margin-bottom: 8px; align-items: center; text-decoration: none; color: inherit; transition: box-shadow 0.2s; direction: rtl; }
        .product-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .product-img { width: 60px; height: 60px; object-fit: cover; border-radius: 4px; margin-left: 10px; flex-shrink: 0; background: #f0f0f0; }
        .product-info { flex: 1; min-width: 0; display: flex; flex-direction: column; justify-content: center; }
        .product-name { font-weight: bold; font-size: 14px; margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: #333; }
        .product-price { color: #eab308; font-weight: bold; font-size: 14px; }
        .product-btn { background: #000; color: #fff; font-size: 12px; padding: 5px 10px; border-radius: 4px; margin-right: auto; white-space: nowrap; }

        /* --- מסך חשוך ברקע (Overlay) --- */
        #shopipet-overlay {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.5); z-index: 2147483646;
            display: none;
        }

        /* --- התאמה למובייל (עד 600px) --- */
        @media (max-width: 600px) {
            #shopipet-window {
                width: 100% !important;
                height: 80% !important; /* מגירה שנפתחת לגובה 80% */
                bottom: 0 !important;
                right: 0 !important;
                left: 0 !important;
                top: auto !important;
                border-bottom-left-radius: 0 !important;
                border-bottom-right-radius: 0 !important;
                border-top-left-radius: 16px !important;
                border-top-right-radius: 16px !important;
                box-shadow: 0 -5px 20px rgba(0,0,0,0.2) !important;
            }
            /* הבועה מוסתרת רק כשהצ'אט פתוח (מטופל ב-JS) */
        }
    `;
    document.head.appendChild(style);

    const overlay = document.createElement('div');
    overlay.id = 'shopipet-overlay';

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
            <input type="text" id="shopipet-input" placeholder="שאל אותי משהו..." autocomplete="off">
            <button id="shopipet-send">שלח</button>
        </div>
    `;

    document.body.appendChild(overlay);
    document.body.appendChild(bubble);
    document.body.appendChild(win);

    // ניהול היסטוריה מקומית (אופציונלי לממשק) - ה-Agent מנהל את הזיכרון האמיתי
    let history = []; 
    
    const toggleChat = () => {
        const isHidden = win.style.display === 'none' || win.style.display === '';
        
        if (isHidden) {
            // -- פתיחה --
            win.style.display = 'flex';
            overlay.style.display = 'block';
            
            // במובייל בלבד: נסתיר את הבועה כשהצ'אט פתוח
            if (window.innerWidth <= 600) {
                document.body.style.overflow = 'hidden'; // מונע גלילה של האתר
                bubble.style.display = 'none';
            }
            
            // פוקוס על שדה הקלט (רק בדסקטופ)
            if (window.innerWidth > 600) {
                setTimeout(() => document.getElementById('shopipet-input').focus(), 100);
            }
        } else {
            // -- סגירה --
            win.style.display = 'none';
            overlay.style.display = 'none';
            document.body.style.overflow = ''; 
            bubble.style.display = 'flex'; // מחזירים את הבועה
        }
    };

    bubble.onclick = toggleChat;
    overlay.onclick = toggleChat;
    document.getElementById('shopipet-close').onclick = toggleChat;

    async function sendMessage() {
        const input = document.getElementById('shopipet-input');
        const text = input.value.trim();
        if (!text) return;

        addMessage(text, 'user');
        input.value = '';
        input.disabled = true;

        // שליפת ה-Thread ID מהזיכרון של הדפדפן (אם קיים)
        const storedThreadId = localStorage.getItem(STORAGE_KEY);

        try {
            const res = await fetch(`${API_BASE}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    message: text, 
                    thread_id: storedThreadId // שולחים את המזהה כדי להמשיך שיחה
                })
            });

            if (!res.ok) throw new Error(`Server error: ${res.status}`);

            const data = await res.json();
            
            // 1. שמירת ה-Thread ID החדש (אם נוצר)
            if (data.thread_id) {
                localStorage.setItem(STORAGE_KEY, data.thread_id);
            }

            // 2. הצגת הודעת הבוט (Agent)
            if (data.message || data.reply) {
                const replyText = data.message || data.reply;
                addMessage(replyText, 'bot');
            }

            // 3. הצגת כרטיסי מוצר (אם ה-Backend שלח כאלה)
            if (data.items && Array.isArray(data.items) && data.items.length > 0) {
                data.items.forEach(item => {
                    addProductCard(item);
                });
            }

            // 4. טיפול בשגיאות
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
        // המרת סימני Markdown בסיסיים אם ה-Agent שולח אותם
        let formattedText = text.replace(/\n/g, '<br>');
        // הסרת הערות שוליים אם נשארו
        formattedText = formattedText.replace(/【.*?】/g, '');
        
        div.innerHTML = formattedText;
        const container = document.getElementById('shopipet-messages');
        container.appendChild(div);
        scrollToBottom();
    }

    function addProductCard(item) {
        const imgUrl = item.image || 'https://placehold.co/60x60?text=Pet';
        
        const card = document.createElement('a');
        card.className = 'product-card';
        card.href = item.url;
        card.target = '_blank';
        
        card.innerHTML = `
            <img src="${imgUrl}" class="product-img" alt="${item.name}">
            <div class="product-info">
                <div class="product-name">${item.name}</div>
                <div class="product-price">${item.price}</div>
            </div>
            <div class="product-btn">לרכישה</div>
        `;
        
        const container = document.getElementById('shopipet-messages');
        container.appendChild(card);
        scrollToBottom();
    }

    function scrollToBottom() {
        const container = document.getElementById('shopipet-messages');
        container.scrollTop = container.scrollHeight;
    }

    document.getElementById('shopipet-send').onclick = sendMessage;
    
    document.getElementById('shopipet-input').onkeypress = (e) => { 
        if (e.key === 'Enter') sendMessage(); 
    }
})();
