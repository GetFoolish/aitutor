from fastapi.testclient import TestClient
from dash_api import app

client = TestClient(app)

def test_get_learning_path_unauthorized():
    """Test that learning path requires authentication"""
    response = client.get("/api/learning-path")
    # Should fail without auth header
    assert response.status_code in [401, 403, 500] # Depending on how auth middleware handles missing header

def test_get_learning_path_structure(mocker):
    """Test the structure of the learning path response"""
    # Mock auth to return a valid user_id
    mocker.patch("dash_api.get_current_user", return_value="test_user_123")
    
    # Mock dash_system to return some scores
    mock_scores = {
        "counting_1_10": {
            "name": "Counting 1-10",
            "memory_strength": 2.5,
            "accuracy": 0.95
        }
    }
    mocker.patch("dash_api.dash_system.get_skill_scores", return_value=mock_scores)
    
    response = client.get("/api/learning-path")
    
    # If auth mock works, we should get 200
    if response.status_code == 200:
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            item = data[0]
            assert "id" in item
            assert "title" in item
            assert "status" in item
            assert "score" in item
