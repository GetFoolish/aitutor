from __future__ import annotations

import argparse
import json
import pathlib
from typing import Iterable

from pymongo.errors import PyMongoError

from config_manager import ConfigManager
from db.config_repository import upsert_config_document
from db.mongo_client import get_client, get_database, ping_database
from db.perseus_repository import upsert_question

ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent
QUESTIONS_BANK_DIR = ROOT_DIR / "QuestionsBank"
PERSEUS_DIR = ROOT_DIR / "SherlockEDApi" / "CurriculumBuilder"


def load_json_file(path: pathlib.Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def iter_perseus_files() -> Iterable[pathlib.Path]:
    return sorted(PERSEUS_DIR.glob("*.json"))


def seed_config() -> None:
    skills = load_json_file(QUESTIONS_BANK_DIR / "skills.json")
    curriculum = load_json_file(QUESTIONS_BANK_DIR / "curriculum.json")

    upsert_config_document("skills", skills)
    upsert_config_document("curriculum", curriculum)


def seed_perseus_questions() -> None:
    for file_path in iter_perseus_files():
        document_id = file_path.stem
        payload = load_json_file(file_path)
        upsert_question(document_id, payload)


def main(drop: bool) -> None:
    if not ping_database():
        raise SystemExit("Unable to connect to MongoDB. Check MONGODB_URI.")

    client = get_client()
    config = ConfigManager()
    db_name = config.get_database_name()

    if drop:
        print(f"Dropping database '{db_name}' before seeding...")
        client.drop_database(db_name)

    seed_config()
    seed_perseus_questions()
    print(f"Seeded MongoDB database '{db_name}'.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed MongoDB with curriculum data.")
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop the target database before seeding.",
    )
    args = parser.parse_args()
    main(drop=args.drop)
