import requests
import json

question_id = "69374f43150db826a8c25657"
url = f"http://localhost:8010/api/question/{question_id}"

print(f"Verifying graph fix for: {url}...")
try:
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        
        # Check image URL in question content or images map
        content = data.get('question', {}).get('content', '')
        images = data.get('question', {}).get('images', {})
        
        print(f"  Images Map keys: {list(images.keys())}")
        
        if "/fixed_graphs/graph_69374.png" in str(data):
            print("  [SUCCESS] Graph now uses the fixed static asset.")
        else:
            print("  [FAILURE] Graph still points to broken URL.")
            
    else:
        print(f"Failed with status: {response.status_code}")
except Exception as e:
    print(f"Error: {e}")
