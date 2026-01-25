import requests
import json

question_id = "693539d0e61eddfd0c726621"
url = f"http://localhost:8010/api/question/{question_id}"

print(f"Verifying asterisk fix for: {url}...")
try:
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        
        # Check image caption
        widgets = data.get('question', {}).get('widgets', {})
        for w_id, w_data in widgets.items():
            if w_data.get('type') == 'image':
                caption = w_data.get('options', {}).get('caption', '')
                print(f"  Widget {w_id} Caption: {repr(caption)}")
                if '*' in caption:
                    print("    !! Caption still has *")
                else:
                    print("    Caption is clean.")
        
        content = data.get('question', {}).get('content', '')
        if '**' in content:
            print(f"  !! Question content still has **: {content[:50]}...")
        else:
            print("  Question content is clean.")
            
    else:
        print(f"Failed with status: {response.status_code}")
except Exception as e:
    print(f"Error: {e}")
