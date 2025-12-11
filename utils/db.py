import os
import redis
import json

# Connect to Vercel KV
r = redis.from_url(os.environ.get("KV_URL"))

def save_catalog(data):
    # שומר את כל הקטלוג בזיכרון
    r.set("shopipet:catalog", json.dumps(data))

def get_catalog():
    data = r.get("shopipet:catalog")
    return json.loads(data) if data else []
