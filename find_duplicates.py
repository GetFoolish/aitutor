
import requests
import json

BASE_URL = "http://localhost:8010/api/questions/search"

def search(query, label):
    print(f"--- Searching for: {label} ---")
    try:
        response = requests.post(BASE_URL, json={"query": query, "limit": 50})
        response.raise_for_status()
        data = response.json()
        
        results = data.get("results", [])
        print(f"Found {len(results)} questions.")
        
        for q in results:
            qid = q.get("_id") or q.get("id")
            content = q.get("question", {}).get("content", "")[:50] + "..."
            print(f"ID: {qid} | Content: {content}")
            
    except Exception as e:
        print(f"Error: {e}")
    print("\n")

if __name__ == "__main__":
    # Search for LaTeX align
    search(r'"begin{align}"', "LaTeX align phrase")
    
    # Search for ###Strategy
    search(r'"###Strategy"', "Header ###Strategy")
