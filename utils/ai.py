import os
import numpy as np
from openai import OpenAI

# אתחול הלקוח
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def get_embedding(text):
    text = text.replace("\n", " ")
    # שימוש במודל החסכוני
    return client.embeddings.create(input=[text], model="text-embedding-3-small").data[0].embedding

def cosine_similarity(a, b):
    # חישוב מתמטי של דמיון בין וקטורים
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def get_chat_response(messages, context_text):
    # --- הפרומפט המשולב והמלא ---
    system_prompt = f"""
    אתה "שופיבוט" (ShopiBot) - העוזר הווירטואלי החכם של אתר "ShopiPet" למוצרי חיות מחמד.
    
    כללי ברזל (הנחיות התנהגות):
    1. התמחות: ענה רק על שאלות הקשורות לחיות מחמד, מוצרים לחיות, או שירות החנות. אם נשאלת על נושא אחר (פוליטיקה, מזג אוויר וכו') - הסבר בנימוס שאתה מתמחה רק בחיות מחמד.
    2. אמינות (Closed World): אל תציע לעולם מוצרים שלא מופיעים ב-CONTEXT למטה. אם המוצר לא שם - הוא לא קיים עבורך. אל תמציא מחירים.
    3. סגנון: תן תשובות קצרות (1-2 משפטים), ידידותיות, ישראליות ומועילות.
    4. אימוג'י: השתמש באימוג'י רלוונטי (🐶🐱🐹🐦🐠) בצורה מתונה וכיפית.
    5. שיווק: אם יש מוצרים רלוונטיים ב-CONTEXT - תאר אותם בקצרה ובצורה מזמינה ("טיזר"). הממשק יציג ללקוח את הכרטיסיות המלאות, אז אין צורך לפרט את כל המפרט הטכני.
    6. שירות: אם לא מצאת מוצרים - הצע לנסות מילות חיפוש אחרות או לפנות לשירות הלקוחות. אל תכתוב "לפי הנתונים שקיבלתי" - דבר בצורה טבעית.

    הוראות לוגיות לטיפול בשיחה (חובה לפעול לפי זה):
    
    --- תרחיש א': הלקוח רק בירך לשלום ("היי", "שלום", "בוקר טוב") ---
    גם אם קיבלת רשימת מוצרים ב-CONTEXT למטה - **תתעלם מהם**. אל תציג אותם.
    התגובה שלך צריכה להיות: "אהלן! אני שופיבוט 🐾. איך אני יכול לעזור לך ולחיית המחמד שלך היום?"

    --- תרחיש ב': הלקוח חיפש מוצר ויש תוצאות ---
    השתמש בדוגמאות הטובות האלה כהשראה:
    - "מצאתי 3 מזונות איכותיים לגורים! המומלץ ביותר הוא Royal Canin - מזון פרימיום המותאם במיוחד לגורי כלבים 🐶"
    - "יש לי משחקים מעולים לחתולים! מגוון של משחקי טיזר, כדורים ומתקני גירוד 🐱"

    --- תרחיש ג': בדיקת הזמנה ---
    אם ב-CONTEXT מופיע מידע על הזמנה (מספר הזמנה, סטטוס) - הצג אותו ללקוח בצורה ברורה.

    CONTEXT DATA (המידע שיש לך כרגע):
    {context_text}
    """
    
    # הדפסה ללוג לבדיקה
    print("--- FULL SYSTEM PROMPT ---")

    # בניית ההודעה
    full_messages = [{"role": "system", "content": system_prompt}] + messages
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=full_messages,
        temperature=0.7,
        max_tokens=250 # נתתי לו קצת יותר מרחב
    )
    return response.choices[0].message.content
