import os
import numpy as np
from openai import OpenAI
import json

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def get_embedding(text):
    text = text.replace("\n", " ")
    return client.embeddings.create(input=[text], model="text-embedding-3-small").data[0].embedding

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# --- פונקציה חדשה: המוח שמבין מה הלקוח רוצה ---
def classify_intent(message):
    """
    מנתח את הודעת המשתמש ומחזיר אחת מהקטגוריות הבאות:
    - search: הלקוח מחפש מוצר, שואל על מחיר, או מתעניין במשהו מהחנות.
    - order: הלקוח שואל על סטטוס הזמנה/משלוח.
    - chat: הלקוח סתם מברך לשלום, מודה, או מדבר שיחת חולין (Small talk).
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a classifier. Classify the user message into one of these JSON values: {'intent': 'search'} (for product questions), {'intent': 'order'} (for shipping/order status), or {'intent': 'chat'} (for greetings, thanks, or general talk). Return ONLY JSON."},
            {"role": "user", "content": message}
        ],
        temperature=0, # דיוק מקסימלי
        response_format={"type": "json_object"} # מכריח תשובה בפורמט JSON
    )
    
    try:
        data = json.loads(response.choices[0].message.content)
        return data.get("intent", "chat")
    except:
        return "chat" # ברירת מחדל

def get_chat_response(messages, context_text):
    # הפרומפט המלא והחכם שלך (ללא קיצורים)
    system_prompt = f"""
    אתה "שופיבוט" (ShopiBot) - העוזר הווירטואלי החכם של אתר "ShopiPet" למוצרי חיות מחמד.
    
    כללי ברזל (הנחיות התנהגות):
    1. התמחות: ענה רק על שאלות הקשורות לחיות מחמד, מוצרים לחיות, או שירות החנות.
    2. אמינות (Closed World): המידע שיש לך על מוצרים הוא אך ורק מה שמופיע ב-CONTEXT למטה. אם רשימת ה-CONTEXT ריקה - זה אומר שאין מוצרים רלוונטיים לשיחה הזו.
    3. סגנון: תן תשובות קצרות (1-2 משפטים), ידידותיות, ישראליות ומועילות.
    4. אימוג'י: השתמש באימוג'י רלוונטי (🐶🐱🐹🐦🐠) בצורה מתונה וכיפית.
    
    תרחישים:
    - אם יש מוצרים ב-CONTEXT: תאר אותם בקצרה ובצורה שיווקית ("מצאתי כמה אופציות מעולות...").
    - אם ה-CONTEXT ריק: נהל שיחה טבעית, שאל איך לעזור, או הפנה לשירות לקוחות. אל תמציא מוצרים.

    CONTEXT DATA:
    {context_text}
    """
    
    full_messages = [{"role": "system", "content": system_prompt}] + messages
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=full_messages,
        temperature=0.7
    )
    return response.choices[0].message.content
