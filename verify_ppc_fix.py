import requests
import json

question_id = "69362807c70527189f059e15"
url = f"http://localhost:8010/api/question/{question_id}"

print(f"Verifying graph fix for: {url}...")
try:
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        
        # Check image 1 URL
        widgets = data.get('question', {}).get('widgets', {})
        w_data = widgets.get('image 1', {})
        bg_url = w_data.get('options', {}).get('backgroundImage', {}).get('url', '')
        print(f"  Widget 'image 1' URL: {repr(bg_url)}")
        
        if "/fixed_graphs/graph_69362.png" in bg_url:
            print("  [SUCCESS] Graph now uses the fixed static asset.")
        else:
            print("  [FAILURE] Graph still points to broken URL.")
            
    else:
        print(f"Failed with status: {response.status_code}")
except Exception as e:
    print(f"Error: {e}")
