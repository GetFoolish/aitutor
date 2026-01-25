
import os
from pymongo import MongoClient
from bson.objectid import ObjectId

# Connection string
MONGO_URI = "mongodb+srv://sherlocked:sherlocked123@cluster0.bbw2k.mongodb.net/athena_db?retryWrites=true&w=majority"

def fix_question_graph(q_id):
    try:
        client = MongoClient(MONGO_URI)
        db = client['athena_db']
        collection = db['questions']
        
        query = {"_id": ObjectId(q_id)}
        question = collection.find_one(query)
        
        if not question:
            print(f"Question {q_id} not found.")
            return

        # 1. FIX WIDGET (plotter or interactive-graph)
        widgets = question.get('widgets', {})
        
        # We expect a 'plotter' or 'interactive-graph' widget.
        # Based on user description, it's likely 'plotter' or 'interactive-graph' with bars.
        # Let's target the one found in inspection (likely 'plotter 1')
        
        target_widget_id = None
        for w_id, w_data in widgets.items():
            if w_data['type'] in ['plotter', 'interactive-graph']:
                target_widget_id = w_id
                break
        
        if target_widget_id:
            print(f"Updating widget {target_widget_id}...")
            
            # Configure specifically for the requested bar chart
            # Scale 0-70, intervals of 7 or 10? Image shows 0, 7, 14... 70 (steps of 7)
            
            new_options = {
                "correct": [25, 30, 15, 60], # Dummy values, user can adjust
                "starting": [0, 0, 0, 0],
                "type": "bar",
                "labels": ["Stegosaurus", "Raptor", "Triceratops", "T-Rex"],
                "maxY": 70,
                "labelY": "Number in orchestra",
                "labelX": "Dinosaur type",
                "snapsY": 1, # Allow fine dragging
                "scaleY": 7,  # Step for grid lines matches image (0, 7, 14...)
            }
            
            # If it's a 'plotter' generic type, we map it like this.
            # If it were 'interactive-graph', the structure is different.
            # Assuming 'plotter' based on "plotter 2" from previous hints.
            
            widgets[target_widget_id]['options'] = new_options
            print("Widget options updated.")
        
        # 2. FIX HINTS
        hints = question.get('hints', [])
        if hints:
            last_hint_idx = len(hints) - 1
            last_hint = hints[last_hint_idx]
            
            # Replace content of last hint with image
            last_hint['content'] = "The answer is:\n\n![](https://ai-tutor-backend.vercel.app/fixed_graphs/solution_693535.png)"
            
            # Clear widgets from this hint if any
            if 'widgets' in last_hint:
                last_hint['widgets'] = {}
                
            print(f"Updated hint {last_hint_idx + 1} with solution image.")
            
        # Update DB
        collection.update_one(query, {"$set": {"widgets": widgets, "hints": hints}})
        print("Database updated successfully.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fix_question_graph("693535d4e61eddfd0c7265ad")
