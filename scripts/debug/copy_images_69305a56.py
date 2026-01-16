
import shutil
import os

files_map = {
    "uploaded_image_0_1768565914618.png": "question_69305a56_main.png",
    "uploaded_image_1_1768565914618.png": "question_69305a56_choice_0.png",
    "uploaded_image_2_1768565914618.png": "question_69305a56_choice_1.png",
    "uploaded_image_3_1768565914618.png": "question_69305a56_choice_2.png",
    "uploaded_image_4_1768565914618.png": "question_69305a56_choice_3.png"
}

source_dir = r"C:\Users\lenovo\.gemini\antigravity\brain\65b32153-5246-4697-9f19-0c0420ddf757"
dest_dir = r"c:\Users\lenovo\Downloads\WorkTask_aitutor\aitutor\frontend\public\fixed_graphs"

os.makedirs(dest_dir, exist_ok=True)

for src_name, dst_name in files_map.items():
    src = os.path.join(source_dir, src_name)
    dst = os.path.join(dest_dir, dst_name)
    try:
        shutil.copy2(src, dst)
        print(f"Copied {src_name} -> {dst_name}")
    except Exception as e:
        print(f"Error copying {src_name}: {e}")
