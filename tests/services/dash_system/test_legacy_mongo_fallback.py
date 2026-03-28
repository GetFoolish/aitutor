from types import SimpleNamespace

import managers.mongodb_manager as mongodb_manager
import services.DashSystem.dash_api as dash_api
import services.DashSystem.dash_system as dash_system_module


class FakeCursor(list):
    def batch_size(self, _size):
        return self


class FakeCollection:
    def __init__(self, documents):
        self._documents = [dict(doc) for doc in documents]

    def count_documents(self, query):
        return len(self.find(query))

    def find(self, query=None, projection=None):
        query = query or {}
        matched = []
        for document in self._documents:
            if _matches_query(document, query):
                matched.append(_apply_projection(document, projection))
        return FakeCursor(matched)


def _matches_query(document, query):
    for key, value in query.items():
        candidate = document.get(key)
        if isinstance(value, dict) and "$in" in value:
            if candidate not in value["$in"]:
                return False
            continue
        if candidate != value:
            return False
    return True


def _apply_projection(document, projection):
    if not projection:
        return dict(document)

    included_keys = {key for key, enabled in projection.items() if enabled}
    if not included_keys:
        return {}

    projected = {}
    for key in included_keys:
        if key in document:
            projected[key] = document[key]
    if "_id" in document and projection.get("_id", 1):
        projected["_id"] = document["_id"]
    return projected


def make_fake_mongo():
    return SimpleNamespace(
        generated_skills=FakeCollection(
            [
                {
                    "skill_id": "41.1.1.1_Count_with_small_numbers",
                    "name": "Count with small numbers",
                    "grade_level": "K",
                    "prerequisites": [],
                    "forgetting_rate": 0.07,
                    "difficulty": 0.0,
                    "order": 1,
                }
            ]
        ),
        scraped_questions=FakeCollection([]),
        skills=FakeCollection(
            [
                {
                    "skill_id": "counting_1_10",
                    "name": "Counting 1-10",
                    "grade_level": "K",
                    "prerequisites": [],
                    "forgetting_rate": 0.05,
                    "difficulty": 0.0,
                    "order": 0,
                }
            ]
        ),
        dash_questions=FakeCollection(
            [
                {
                    "question_id": "k_count_1",
                    "content": "Count from 1 to 5: 1, 2, 3, ?, ?",
                    "correct_answer": "4, 5",
                    "difficulty": 0.1,
                    "expected_time_seconds": 30,
                    "skill_id": "counting_1_10",
                },
                {
                    "question_id": "k_count_2",
                    "content": "How many fingers am I holding up? (Show 7)",
                    "correct_answer": "7",
                    "difficulty": 0.2,
                    "expected_time_seconds": 20,
                    "skill_id": "counting_1_10",
                },
                {
                    "question_id": "k_count_3",
                    "content": "How many toes are you showing? (Show 9)",
                    "correct_answer": "9",
                    "difficulty": 0.2,
                    "expected_time_seconds": 20,
                    "skill_id": "counting_1_10",
                },
                {
                    "question_id": "k_count_4",
                    "content": "How many fingers are you showing? (Show 8)",
                    "correct_answer": "8",
                    "difficulty": 0.2,
                    "expected_time_seconds": 20,
                    "skill_id": "counting_1_10",
                },
            ]
        ),
    )


def test_dash_system_falls_back_to_legacy_mongo_dataset(monkeypatch):
    fake_mongo = make_fake_mongo()
    monkeypatch.setattr(mongodb_manager, "mongo_db", fake_mongo)
    monkeypatch.setattr(dash_system_module, "UserManager", lambda *args, **kwargs: SimpleNamespace())

    dash_system = dash_system_module.DASHSystem(use_mongodb=True)

    assert dash_system.question_data_mode == "legacy"
    assert set(dash_system.skills) == {"counting_1_10"}
    assert dash_system.question_index == {"k_count_1": "counting_1_10", "k_count_2": "counting_1_10", "k_count_3": "counting_1_10", "k_count_4": "counting_1_10"}
    assert dash_system.skill_question_index["counting_1_10"] == ["k_count_1", "k_count_2", "k_count_3", "k_count_4"]


def test_load_perseus_items_synthesizes_legacy_radio_questions(monkeypatch):
    fake_mongo = make_fake_mongo()
    monkeypatch.setattr(mongodb_manager, "mongo_db", fake_mongo)
    monkeypatch.setattr(
        dash_api,
        "dash_system",
        SimpleNamespace(
            question_data_mode="legacy",
            skills={"counting_1_10": SimpleNamespace(name="Counting 1-10")},
        ),
    )

    dash_question = dash_system_module.Question(
        question_id="k_count_1",
        skill_ids=["counting_1_10"],
        content="",
        difficulty=0.1,
        expected_time_seconds=30.0,
    )

    items = dash_api.load_perseus_items_for_dash_questions_from_mongodb([dash_question])

    assert len(items) == 1
    item = items[0]
    assert item["dash_metadata"]["dash_question_id"] == "k_count_1"
    assert item["dash_metadata"]["skill_names"] == ["Counting 1-10"]
    assert item["question"]["content"].endswith("[[☃ radio 1]]\n")

    radio_widget = item["question"]["widgets"]["radio 1"]
    assert radio_widget["type"] == "radio"
    assert radio_widget["options"]["multipleSelect"] is False

    choices = radio_widget["options"]["choices"]
    assert len(choices) == 4
    assert sum(1 for choice in choices if choice["correct"]) == 1
    assert any(choice["content"] == "4, 5" and choice["correct"] for choice in choices)
