import os
import redis
import json

# שימוש במשתנה הקיים אצלך
redis_url = os.environ.get("shopipetbot_REDIS_URL")

# תיקון: מחקנו את ssl_cert_reqs=None שגרם לשגיאה
r = redis.from_url(redis_url)

def save_catalog(data):
    r.set("shopipet:catalog", json.dumps(data))

def get_catalog():
    data = r.get("shopipet:catalog")
    return json.loads(data) if data else []
