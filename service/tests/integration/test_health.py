import os
import requests

def test_healthcheck():
    base_url = os.getenv("BASE_URL", "http://localhost:5000")

    url = f"{base_url}/health"
    r = requests.get(url, timeout=5)
    assert r.status_code == 200
    # opcional: validar payload
    # assert r.json().get("status") == "ok"
