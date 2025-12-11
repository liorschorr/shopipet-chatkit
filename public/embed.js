(function() {
    // וודא שזו הכתובת שלך!
    const API_BASE = "https://shopipet-chatkit.vercel.app/api"; 

    const style = document.createElement('style');
    style.innerHTML = `
        /* שינוי צבע לצהוב-זהב (#eab308) וטקסט שחור לקונטרסט */
        #shopipet-bubble { position: fixed; bottom: 20px; right: 20px; width: 60px; height: 60px; background: #eab308; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; color: black; font-size: 30px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); z-index: 9999; }
        #shopipet-window { position: fixed; bottom: 90px; right: 20px; width: 350px; height: 500px; background: white; border-radius: 12px; box-shadow: 0 5px 20px rgba(0,0,0,0.2); display: none; flex-direction: column; z-index: 9999; overflow: hidden; font-family: sans-serif; direction: rtl; }
        
        /* כותרת צהובה עם טקסט שחור */
        #shopipet-header { background: #eab308; color: black; padding: 15px; font-weight: bold; }
        
        #shopipet-messages { flex: 1; padding: 15px; overflow-y: auto; background: #f9f9f9; }
        #shopipet-input-area { padding: 10px; border-top: 1px solid #eee; display: flex; }
        #shopipet-input { flex: 1; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
        
        /* כפתור שליחה צהוב */
        #shopipet-send { margin-right: 10px; padding: 8px 15px; background: #eab308; color: black; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; }
        
        .msg { margin-bottom: 10px; padding: 8px 12px; border-radius: 8px; max-width: 80%; font-size: 14px; }
        .msg.user { background: #fff9c4; align-self: flex-end; margin-right: auto; } /* צהוב בהיר מאוד למשתמש */
        .msg.bot { background: #fff; border: 1px solid #ddd; align-self: flex-start; }
        .msg.error { background: #ffebee; color: #c62828; border: 1px solid #ffcdd2; direction: ltr; text-align: left; }
    `;
    document.head.appendChild(style);

    const bubble = document.createElement('div');
    bubble.id = 'shopipet-bubble';
    bubble.innerHTML = '🐾';
    
    const win = document.createElement('div');
    win.id = 'shopipet-window';
    win.innerHTML = `
        <div id="shopipet-header">שופיבוט</div>
        <div id="shopipet-messages"></div>
        <div id="shopipet-input-area">
            <input type="text" id="shopipet-input" placeholder="כתוב הודעה...">
            <button id="shopipet-send">שלח</button>
        </div>
    `;

    document.body.appendChild(bubble);
    document.body.appendChild(win);

    let history = [];
    
    bubble.onclick = () => { win.style.display = win.style.display === 'none' ? 'flex' : 'none'; };

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

            if (!res.ok) {
                const errText = await res.text();
                throw new Error(`Server Error (${res.status}): ${errText}`);
            }

            const data = await res.json();
            
            if (data.reply) {
                addMessage(data.reply, 'bot');
                history.push({ role: 'user', content: text });
                history.push({ role: 'assistant', content: data.reply });
            } 
            else if (data.error) {
                addMessage(`Server Logic Error: ${data.error}`, 'error');
            }
            else {
                addMessage(`Unknown response: ${JSON.stringify(data)}`, 'error');
            }

        } catch (e) {
            addMessage(`Client Error: ${e.message}`, 'error');
        }
        input.disabled = false;
        input.focus();
    }

    function addMessage(text, sender) {
        const div = document.createElement('div');
        div.className = `msg ${sender}`;
        div.innerText = text;
        document.getElementById('shopipet-messages').appendChild(div);
        document.getElementById('shopipet-messages').scrollTop = 99999;
    }

    document.getElementById('shopipet-send').onclick = sendMessage;
    document.getElementById('shopipet-input').onkeypress = (e) => { if (e.key === 'Enter') sendMessage(); }
})();
