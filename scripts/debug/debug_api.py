
import requests
import json

url = "http://localhost:8010/api/question/691c6d6a41372912898cd7ae"
try:
    response = requests.get(url)
    data = response.json()
    print(f"STATUS: {response.status_code}")
    print(f"KEYS: {list(data.keys())}")
    if 'perseusItem' in data:
        p = data['perseusItem']
        if p:
            print(f"PERSEUS ITEM KEYS: {list(p.keys())}")
            if 'question' in p:
                print(f"QUESTION KEYS: {list(p['question'].keys())}")
                print(f"CONTENT PREVIEW: {p['question'].get('content', '')[:100]}...")
            else:
                print("❌ 'question' MISSING in perseusItem")
        else:
            print("❌ 'perseusItem' is NULL")
    else:
        print("❌ 'perseusItem' MISSING in response")
except Exception as e:
    print(f"ERROR: {e}")
