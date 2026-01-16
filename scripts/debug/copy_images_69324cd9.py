
import shutil
import os

source_dir = r"C:\Users\lenovo\.gemini\antigravity\brain\65b32153-5246-4697-9f19-0c0420ddf757"
dest_dir = r"c:\Users\lenovo\Downloads\WorkTask_aitutor\aitutor\frontend\public\fixed_graphs"

os.makedirs(dest_dir, exist_ok=True)

images = {
    "uploaded_image_0_1768572270319.png": "question_69324cd9_forest.png",
    "uploaded_image_1_1768572270319.png": "question_69324cd9_graph_1.png",
    "uploaded_image_2_1768572270319.png": "question_69324cd9_graph_2.png",
    "uploaded_image_3_1768572270319.png": "question_69324cd9_graph_3.png"
}

for src_name, dest_name in images.items():
    src_path = os.path.join(source_dir, src_name)
    dest_path = os.path.join(dest_dir, dest_name)
    try:
        shutil.copy2(src_path, dest_path)
        print(f"Successfully copied {src_name} to {dest_name}")
    except Exception as e:
        print(f"Error copying {src_name}: {e}")
