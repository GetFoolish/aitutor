import requests
import json

question_id = "69397f3b93ffc72ddaed8fb5"
url = f"http://localhost:8010/api/question/{question_id}"

print(f"Verifying LaTeX fix for: {url}...")
try:
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        content = data.get('question', {}).get('content', '')
        print(f"API Content Received: {repr(content)}")
        
        if r"array{r}" in content:
            print("  [SUCCESS] LaTeX now uses 'array{r}' for alignment.")
        elif r"align" in content:
            print("  [FAILURE] LaTeX still uses 'align'.")
        else:
            print("  [CHECK] Neither 'array{r}' nor 'align' found in content.")
            
        with open('final_fix_verify.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
    else:
        print(f"Failed with status: {response.status_code}")
except Exception as e:
    print(f"Error: {e}")
