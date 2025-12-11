import os
import redis
import json

# שינוי: שימוש במשתנה הקיים אצלך
redis_url = os.environ.get("shopipetbot_REDIS_URL")

# במקרים מסוימים נדרש להוסיף ssl_cert_reqs=None כדי למנוע שגיאות תעודה
r = redis.from_url(redis_url, ssl_cert_reqs=None)

def save_catalog(data):
    r.set("shopipet:catalog", json.dumps(data))

def get_catalog():
    data = r.get("shopipet:catalog")
    return json.loads(data) if data else []
