
import sys
import os
from bson import ObjectId
from shared.logging_config import get_logger

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

# IDs from Recruiter Feedback
RECRUITER_IDS = [
    "691c6e2f41372912898cd98d", # Perseus/Athena display issues
    "691c693241372912898ccd8b", # Bold/Color formatting
    "691c6ace41372912898cd1fb", # Font size mismatch
    "691c6dde41372912898cd8cc", # Widget Error
    "691c6d7741372912898cd7d5", # Radio 0/1 Bug
    "691c6d6a41372912898cd7ae"  # Chart Labels missing
]

# IDs Found in Real DB
REAL_DB_IDS = [
    "692fac057e334152c5f473e5", # Graph (Real)
    "692f198f0a3ad6a639ce934d", # Radio (Real)
    "692fb45f7e334152c5f474d2", # Dropdown (Real)
    "692f1731f13be434de20c0c6", # Numeric/Format (Real)
    "692f1792f13be434de20c0d1"  # Image (Real)
]

def check_id(qid):
    try:
        if not ObjectId.is_valid(qid):
            return "INVALID_FORMAT"
        doc = mongo_db.scraped_questions.find_one({'_id': ObjectId(qid)})
        return "EXISTS" if doc else "MISSING"
    except:
        return "ERROR"

def verify():
    print(f"{'ID':<30} | {'SOURCE':<15} | {'STATUS':<10}")
    print("-" * 60)
    
    for qid in RECRUITER_IDS:
        status = check_id(qid)
        print(f"{qid:<30} | {'Recruiter':<15} | {status:<10}")

    print("-" * 60)

    for qid in REAL_DB_IDS:
        status = check_id(qid)
        print(f"{qid:<30} | {'Real DB':<15} | {status:<10}")

if __name__ == "__main__":
    verify()
