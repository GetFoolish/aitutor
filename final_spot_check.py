import requests
import json

# Target ID and one of the newly fixed IDs
ids_to_check = ["692fb4ae7e334152c5f474dd", "69340807928d27211812264d"]

print("Final API spot check...")
for q_id in ids_to_check:
    url = f"http://localhost:8010/api/question/{q_id}"
    try:
        resp = requests.get(url)
        if resp.status_code == 200:
            content = resp.json().get('question', {}).get('content', '')
            has_bold = "**" in content
            print(f"ID {q_id}: {'DIRTY!!' if has_bold else 'CLEAN'}")
            if has_bold:
                print(f"  Snippet: {repr(content[content.find('**'):content.find('**')+40])}")
        else:
            print(f"ID {q_id}: Failed to fetch ({resp.status_code})")
    except Exception as e:
        print(f"ID {q_id}: Error {e}")
