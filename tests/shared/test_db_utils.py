from shared import db_utils


def test_pagination_params_and_paginated_response():
    params = db_utils.PaginationParams(page=0, limit=500, max_limit=50)
    response = db_utils.paginate(items=["a", "b"], total=5, page=2, limit=2)

    assert params.page == 1
    assert params.limit == 50
    assert params.offset == 0
    assert params.to_dict() == {"page": 1, "limit": 50, "offset": 0}

    assert response.total_pages == 3
    assert response.has_next is True
    assert response.has_prev is True
    assert response.to_dict()["pagination"]["total"] == 5


def test_query_monitor_tracks_slow_queries(monkeypatch):
    monitor = db_utils.QueryMonitor(slow_query_threshold=0.5)
    monkeypatch.setattr(db_utils.time, "time", lambda: 123.45)

    for _ in range(6):
        monitor.monitor_query("users.by_email", execution_time=0.7, params={"email": "a@example.com"})

    monitor.monitor_query("questions.by_topic", execution_time=0.2)

    slow_queries = monitor.get_slow_queries()
    recommendations = monitor.get_recommendations()

    assert len(slow_queries) == 6
    assert slow_queries[0]["timestamp"] == 123.45
    assert recommendations == ["Consider adding index for 'users.by_email' (executed 6 times slowly)"]
    assert "users" in db_utils.INDEX_RECOMMENDATIONS
