from pathlib import Path

file_pattern = Path(__file__).parent.resolve() / "examples" / "*.json"
new_json_path = Path(__file__).parent.resolve() / "new"
from pathlib import Path
path = Path(__file__).parent.resolve() / "new" / Path("s.json").stem
# path = str(path)
print(path)
print(path.split("/")[-1].removesuffix(".json"))
