import os
import re
import json

# Pattern: \left\|\left| ... \right|\right|
# This happens when double bars and single bars are nested incorrectly or redundant.
# We will replace \left\|\left| with \left\| and \right|\right| with \right\|

def fix_latex_errors(repo_path):
    print(f"Scanning {repo_path} for LaTeX errors...")
    count = 0
    fixed_files = 0
    
    for root, dirs, files in os.walk(repo_path):
        for file in files:
            if file.endswith('.json'):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Check for the specific bad pattern
                    # Regex for \left\|\left| (escape backslashes for python string + regex)
                    # Python string: "\\left\\|\\left|"
                    # Regex expecting: \\left\\\|\\left\|
                    
                    new_content = content
                    
                    # Fix 1: The specific Start pattern
                    # Look for \left\|\left|
                    if "\\left\\|\\left|" in new_content:
                         print(f"Found bad start pattern in {file}")
                         new_content = new_content.replace("\\left\\|\\left|", "\\left\\|")
                         
                    # Fix 2: The specific End pattern
                    # Look for \right|\right| (which closes single then single, but we want single then double? Or just fix redundancy)
                    # If we replaced start with `\left\|`, we have one open double.
                    # The original had: OpenDouble, OpenSingle ... CloseSingle, CloseSingle.
                    # If we change start to OpenDouble, we have: OpenDouble ... CloseSingle, CloseSingle.
                    # We need to change CloseSingle, CloseSingle (\right|\right|) to CloseDouble (\right\|).
                    
                    if "\\right|\\right|" in new_content:
                         print(f"Found bad end pattern in {file}")
                         new_content = new_content.replace("\\right|\\right|", "\\right\\|")

                    # Also check for the mismatch reported: \left\| ... \right|
                    # This is harder to regex safely without parsing, but we can look for specific strings if known.
                    
                    if new_content != content:
                        print(f"Fixing {file}...")
                        with open(path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        fixed_files += 1
                        count += 1
                        
                except Exception as e:
                    print(f"Error reading {path}: {e}")

    print(f"Done. Fixed {count} issues in {fixed_files} files.")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    repo_path = os.path.join(current_dir, "temp_content_repo")
    fix_latex_errors(repo_path)
