from types import SimpleNamespace

from fastapi.testclient import TestClient

import services.DashSystem.dash_api as dash_api


class DummyDashSystem:
    def load_user_or_create(self, user_id):
        return SimpleNamespace(question_history=[])

    def get_skill_scores(self, user_id, current_time):
        return {
            "counting_1_10": {
                "name": "Counting 1-10",
                "memory_strength": 2.5,
                "practice_count": 4,
                "correct_count": 3,
            }
        }

    def get_student_state(self, user_id, skill_id):
        return SimpleNamespace(last_practice_time=123.45)


def create_client(monkeypatch):
    original_startup = list(dash_api.app.router.on_startup)
    dash_api.app.router.on_startup.clear()
    monkeypatch.setattr(dash_api, "dash_system", DummyDashSystem())
    client = TestClient(dash_api.app)
    return client, original_startup


def restore_startup(original_startup):
    dash_api.app.router.on_startup[:] = original_startup


def test_skill_scores_requires_authentication(monkeypatch):
    client, original_startup = create_client(monkeypatch)
    try:
        response = client.get("/api/skill-scores")
    finally:
        client.close()
        restore_startup(original_startup)

    assert response.status_code == 401


def test_skill_scores_response_shape(monkeypatch):
    monkeypatch.setattr(dash_api, "get_current_user", lambda request: "user-123")

    client, original_startup = create_client(monkeypatch)
    try:
        response = client.get("/api/skill-scores", headers={"Authorization": "Bearer test-token"})
    finally:
        client.close()
        restore_startup(original_startup)

    assert response.status_code == 200
    assert response.json() == {
        "skill_states": {
            "counting_1_10": {
                "name": "Counting 1-10",
                "memory_strength": 2.5,
                "last_practice_time": 123.45,
                "practice_count": 4,
                "correct_count": 3,
            }
        }
    }
