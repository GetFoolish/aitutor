
import requests

def search_duplicates():
    url = "http://localhost:8010/api/questions/search"
    query = "g(b)=5b-9"
    
    print(f"Searching for duplicates of {query}...")
    try:
        resp = requests.post(url, json={"query": query, "limit": 20})
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            print(f"Found {len(results)} potential duplicates:")
            for item in results:
                print(f"ID: {item['_id']} | Slug: {item.get('slug', 'N/A')}")
        else:
            print(f"Error: {resp.status_code}")
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    search_duplicates()
