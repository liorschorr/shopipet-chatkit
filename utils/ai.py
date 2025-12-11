import os
import numpy as np
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def get_embedding(text):
    text = text.replace("\n", " ")
    # שימוש במודל החסכוני והחדש
    return client.embeddings.create(input=[text], model="text-embedding-3-small").data[0].embedding

def cosine_similarity(a, b):
    # חישוב מתמטי של דמיון בין וקטורים
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def get_chat_response(messages, context_text):
    system_prompt = f"""
    You are ShopiPet, a helpful AI assistant for a pet store.
    
    RULES:
    1. Use ONLY the provided CONTEXT to answer product questions. 
    2. If the answer is not in the context, say "אין לי מידע על כך כרגע".
    3. Be friendly and use emojis occasionally (every 2-3 messages).
    4. Provide answers in Hebrew unless asked otherwise.
    
    CONTEXT:
    {context_text}
    """
    
    # הוספת הנחיית המערכת להיסטוריית השיחה
    full_messages = [{"role": "system", "content": system_prompt}] + messages
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=full_messages,
        temperature=0.7
    )
    return response.choices[0].message.content
