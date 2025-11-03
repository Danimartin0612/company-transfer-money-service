import os
import requests

def test_healthcheck():
    base_url = os.getenv("BASE_URL", "http://localhost:5000")
    r = requests.get(f"{base_url}/health", timeout=5)
    assert r.status_code == 200
    assert r.json().get("status") == "ok"
