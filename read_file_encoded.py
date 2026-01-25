import os

def read_utf16(path):
    try:
        with open(path, 'r', encoding='utf-16') as f:
            print(f.read())
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    path = r"c:\Users\lenovo\Downloads\WorkTask_aitutor\aitutor\question_69319915.json"
    read_utf16(path)
