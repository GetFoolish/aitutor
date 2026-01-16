import requests
import json

def check_api_q():
    url = "http://localhost:8010/api/question/69324cd92e5f91c2481807bc"
    try:
        resp = requests.get(url)
        data = resp.json()
        print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_api_q()
