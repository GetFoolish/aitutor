
import os
from pymongo import MongoClient
from bson.objectid import ObjectId

# Connection string
MONGO_URI = "mongodb+srv://sherlocked:sherlocked123@cluster0.bbw2k.mongodb.net/athena_db?retryWrites=true&w=majority"

def fix_hint_widget(q_id):
    try:
        client = MongoClient(MONGO_URI)
        db = client['athena_db']
        collection = db['questions']
        
        query = {"_id": ObjectId(q_id)}
        question = collection.find_one(query)
        
        if not question:
            print(f"Question {q_id} not found.")
            return

        hints = question.get('hints', [])
        modified = False
        
        for i, hint in enumerate(hints):
            content = hint.get('content', '')
            if '[[Widget: plotter 2' in content:
                print(f"Found broken widget in hint {i+1}")
                # Replace with the new image URL
                # Using absolute path from web root
                new_content = content.replace(
                    '[[Widget: plotter 2 (plotter)]]', 
                    '\n\n![](https://ai-tutor-backend.vercel.app/fixed_graphs/hint_graph_693535.png)\n\n'
                )
                # Fallback for variation without (plotter) type
                new_content = new_content.replace(
                    '[[Widget: plotter 2]]', 
                     '\n\n![](https://ai-tutor-backend.vercel.app/fixed_graphs/hint_graph_693535.png)\n\n'
                )
                
                hint['content'] = new_content
                # Remove the widget reference to prevent any hydration attempts
                if 'widgets' in hint and 'plotter 2' in hint['widgets']:
                    del hint['widgets']['plotter 2']
                
                modified = True
                print("Replaced widget with image.")

        if modified:
            collection.update_one(query, {"$set": {"hints": hints}})
            print("Successfully updated question hints.")
        else:
            print("No matching widget placeholder found in hints.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fix_hint_widget("693535d4e61eddfd0c7265ad")
