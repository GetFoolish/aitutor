
import os
import sys
from bson.objectid import ObjectId

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def investigate_variants():
    snippet = "ratios for angle measures"
    query = {"question.content": {"$regex": snippet}}
    
    docs = list(mongo_db.scraped_questions.find(query))
    print(f"Total variants in family: {len(docs)}")
    
    updated_ids = [
        "69301184ebf6442f98aa9770", "69302916046cc6e7b0047c80", "693076c473cb28d3e4ce42aa",
        "6930c478f2039508cf146ceb", "6930fb0f60f24faf726eb85c", "69312caa216f700652e32607",
        "69316384e99ceba44f0ed5cf", "693199ab8189149cdbee41b9", "6931df357be5c6b2e29cc92b",
        "693285981a6b9ad706c7daab", "6932ef00488c4a5c22f22fee", "69335edf46bd2cf873ae9daa",
        "6933970020538a6f3167f7bc", "6934efc2cd4923e2c34531d0", "6935615970be2a4e56f9f300",
        "69359a4f7eb357b3c8738546", "69360b810aabe66864660c1a", "69367e1bbe093d84ab4ec5ff"
    ]
    
    non_updated = [doc for doc in docs if str(doc['_id']) not in updated_ids]
    print(f"Non-updated variants: {len(non_updated)}")
    
    if non_updated:
        sample = non_updated[0]
        print(f"\nSample Non-Updated ID: {sample['_id']}")
        widgets = sample.get('question', {}).get('widgets', {})
        for name, data in widgets.items():
             if data.get('type') == 'image':
                 print(f"  Widget '{name}' URL: {data.get('options', {}).get('backgroundImage', {}).get('url')}")
             elif data.get('type') == 'radio':
                 print(f"  Widget '{name}' (radio)")

if __name__ == "__main__":
    investigate_variants()
