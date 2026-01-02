
import os

game_file = r"c:\Users\lenovo\Downloads\WorkTask_aitutor\aitutor\services\athenaAPI\app\question_loader.py"

with open(game_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip = False
mock_check_skip = False

for i, line in enumerate(lines):
    # Detect start of broken mock data
    if "# 1. Compare View & Responsiveness" in line:
        skip = True
    
    # Detect end of broken mock data (start of function)
    if "def get_question_by_id" in line:
        skip = False
    
    # Logic to remove the MOCK_QUESTIONS check inside the function
    if "CHECK MOCK DATA FIRST" in line:
        mock_check_skip = True
        continue # Skip this line
        
    if mock_check_skip:
        # We skip lines until we see "Validate ObjectId format" or blank line before it
        if "Validate ObjectId format" in line:
            mock_check_skip = False
            # Don't continue, we want to keep this line
        else:
            continue # Skip the lines inside the mock check block

    if not skip:
        new_lines.append(line)

# Write back
with open(game_file, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Successfully cleaned question_loader.py")
