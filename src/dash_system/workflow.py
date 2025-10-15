from typing import Dict, Optional
from pymongo.collection import Collection
from .db import get_db


class CurriculumWorkflow:
    def __init__(self, pending_skills: Optional[Collection] = None, skills: Optional[Collection] = None):
        db = get_db()
        self.pending_skills: Collection = pending_skills or db["pending_skills"]
        self.skills: Collection = skills or db["skills"]

    def propose_skill(self, skill_doc: Dict) -> str:
        skill_id = skill_doc.get("_id")
        if not skill_id:
            raise ValueError("_id is required for proposed skill")
        skill_doc = {
            **skill_doc,
            "status": "pending",
        }
        self.pending_skills.update_one({"_id": skill_id}, {"$set": skill_doc}, upsert=True)
        return skill_id

    def approve_skill(self, skill_id: str) -> bool:
        doc = self.pending_skills.find_one({"_id": skill_id})
        if not doc:
            return False
        doc.pop("status", None)
        self.skills.update_one({"_id": doc["_id"]}, {"$set": doc}, upsert=True)
        self.pending_skills.delete_one({"_id": skill_id})
        return True

    def list_pending(self):
        return list(self.pending_skills.find({}))
