import os
import re

def fix_latex_mismatch(repo_path):
    print(f"Scanning {repo_path} for LaTeX mismatches...")
    
    # We are looking for \left\| (double) closed by \right| (single)
    # or redundant patterns like \left\|\left|
    
    # In JSON, these are escaped. 
    # \left\|  -> \\left\\|
    # \left|   -> \\left|
    
    patterns = [
        (re.compile(r'\\left\\\|\\left\|'), r'\\left\\\|'), # Fix triple bar to double
        (re.compile(r'\\right\|\\right\|'), r'\\right\\\|'), # Fix double single closes to double close
        (re.compile(r'\\left\\\|(.*?)\\right\|(?![\\|])'), r'\\left\\\|\1\\right\\\|'), # Fix double open with single close
    ]
    
    file_count = 0
    fixed_count = 0
    
    for root, dirs, files in os.walk(repo_path):
        if 'node_modules' in dirs: dirs.remove('node_modules')
        if '.git' in dirs: dirs.remove('.git')
        
        for file in files:
            if file.endswith('.json'):
                path = os.path.join(root, file)
                try:
                    # Try utf-16 first (as we saw it earlier), then utf-8
                    content = None
                    encoding_used = None
                    for enc in ['utf-16', 'utf-8', 'utf-16le', 'latin-1']:
                        try:
                            with open(path, 'r', encoding=enc) as f:
                                content = f.read()
                                encoding_used = enc
                            break
                        except:
                            continue
                            
                    if content is None:
                        continue
                        
                    new_content = content
                    for pattern, replacement in patterns:
                        new_content = pattern.sub(replacement, new_content)
                    
                    if new_content != content:
                        print(f"FIXED: {path} ({encoding_used})")
                        with open(path, 'w', encoding=encoding_used) as f:
                            f.write(new_content)
                        fixed_count += 1
                except Exception as e:
                    print(f"Error processing {path}: {e}")
                file_count += 1
                
    print(f"Done. Scanned {file_count} files, fixed {fixed_count}.")

if __name__ == "__main__":
    # Scan both temp_content_repo and the current root for floating json files
    aitutor_root = r"c:\Users\lenovo\Downloads\WorkTask_aitutor\aitutor"
    fix_latex_mismatch(aitutor_root)
