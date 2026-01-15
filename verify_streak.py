import ast
import sys

# Read the user_manager.py file
with open('./managers/user_manager.py', 'r') as f:
    source = f.read()

# Parse the AST
tree = ast.parse(source)

# Find the UserManager class
user_manager_class = None
for node in ast.walk(tree):
    if isinstance(node, ast.ClassDef) and node.name == 'UserManager':
        user_manager_class = node
        break

if not user_manager_class:
    print("ERROR: UserManager class not found")
    sys.exit(1)

# Check for update_streak or calculate_streak method
method_names = [m.name for m in user_manager_class.body if isinstance(m, ast.FunctionDef)]

if 'update_streak' in method_names or 'calculate_streak' in method_names:
    print('OK')
    sys.exit(0)
else:
    print(f"ERROR: Missing streak calculation method. Found methods: {method_names}")
    sys.exit(1)
