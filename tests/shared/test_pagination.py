import base64

import pytest

from shared.pagination import PaginationCursor, paginate_list, paginate_query


class FakeCursor:
    def __init__(self, items):
        self.items = list(items)

    def sort(self, field, direction):
        reverse = direction == -1
        self.items = sorted(self.items, key=lambda item: item[field], reverse=reverse)
        return self

    def limit(self, count):
        self.items = self.items[:count]
        return self.items


class FakeCollection:
    def __init__(self, items):
        self.items = list(items)

    def find(self, query):
        filtered = self.items
        for field, condition in query.items():
            if isinstance(condition, dict):
                if "$lt" in condition:
                    filtered = [item for item in filtered if item[field] < condition["$lt"]]
                if "$gt" in condition:
                    filtered = [item for item in filtered if item[field] > condition["$gt"]]
            else:
                filtered = [item for item in filtered if item[field] == condition]
        return FakeCursor(filtered)


def test_pagination_cursor_round_trip():
    cursor = PaginationCursor(last_id="abc", last_value=5)
    encoded = cursor.encode()

    decoded = PaginationCursor.decode(encoded)

    assert decoded.last_id == "abc"
    assert decoded.last_value == 5


def test_pagination_cursor_rejects_invalid_value():
    with pytest.raises(ValueError, match="Invalid cursor"):
        PaginationCursor.decode("not-a-cursor")


def test_paginate_list_uses_cursor():
    result = paginate_list(["a", "b", "c", "d"], limit=2)
    follow_up = paginate_list(["a", "b", "c", "d"], cursor=result.next_cursor, limit=2)

    assert result.items == ["a", "b"]
    assert result.has_more is True
    assert follow_up.items == ["c", "d"]
    assert follow_up.has_more is False


def test_paginate_query_builds_next_cursor():
    collection = FakeCollection(
        [
            {"_id": "1", "score": 10},
            {"_id": "2", "score": 8},
            {"_id": "3", "score": 6},
        ]
    )

    first_page = paginate_query(collection, query={}, limit=2, sort_field="score", sort_descending=True)
    second_page = paginate_query(
        collection,
        query={},
        cursor=first_page.next_cursor,
        limit=2,
        sort_field="score",
        sort_descending=True,
    )

    assert [item["_id"] for item in first_page.items] == ["1", "2"]
    assert first_page.has_more is True
    assert [item["_id"] for item in second_page.items] == ["3"]
    assert second_page.has_more is False
