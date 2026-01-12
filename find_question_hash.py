
import os
import sys
# Add the service directory to path so we can import app modules if needed
sys.path.append(os.path.join(os.getcwd(), 'services', 'athenaAPI'))

# It seems we can't easily import the app modules without setting up the environment.
# But we can try to connect to the DB directly if we know the URI, or checks the file based loaders.
# Let's try to search in the 'questions' collection if we can connect to mongo.

# Assuming run_backend.py sets up a mongo client.
# Let's try to look for JSON files first as that might be faster if it is file based.

def search_files_for_id(directory, target_id):
    print(f"Searching for {target_id} in {directory}...")
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.json'):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if target_id in content:
                            print(f"Found ID in file: {path}")
                            # Print a snippet around the ID
                            idx = content.find(target_id)
                            start = max(0, idx - 500)
                            end = min(len(content), idx + 2000)
                            print(content[start:end])
                            return True
                except Exception as e:
                    pass
    return False

# Search in the whole project? That might be slow.
# Let's look at `services/athenaAPI/app` or `data` if it exists.
base_dir = os.getcwd()
print(f"Base Dir: {base_dir}")

found = search_files_for_id(os.path.join(base_dir, 'services', 'athenaAPI'), '6933b3176cf86fa761d0a255')
if not found:
    print("Not found in athenaAPI files.")

