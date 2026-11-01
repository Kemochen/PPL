"""Call the existing WSGI application in memory. No socket/server is started."""
import json
from app import app

client = app.test_client()


def dispatch(path, method, body, is_json):
    if not path.startswith("/api/") or method not in ("GET", "POST"):
        raise ValueError("Unknown local operation")
    values = json.loads(body)
    options = {"json": values} if is_json else {"data": values}
    response = client.open(path, method=method, **options)
    return json.dumps({"status": response.status_code, "body": response.get_json()})
