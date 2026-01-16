
import shutil
import os

source_path = r"C:\Users\lenovo\.gemini\antigravity\brain\65b32153-5246-4697-9f19-0c0420ddf757\uploaded_image_1768567372062.png"
dest_path = r"c:\Users\lenovo\Downloads\WorkTask_aitutor\aitutor\frontend\public\fixed_graphs\question_6930ae80_main.png"

os.makedirs(os.path.dirname(dest_path), exist_ok=True)

try:
    shutil.copy2(source_path, dest_path)
    print(f"Successfully copied image to {dest_path}")
except Exception as e:
    print(f"Error copying image: {e}")
