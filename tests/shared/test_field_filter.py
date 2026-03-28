import asyncio

from shared import field_filter


class ExampleResponse(field_filter.FilterableResponse):
    user_id: str
    name: str
    email: str


def test_filter_fields_and_parse_query():
    data = {"user_id": "user-123", "name": "Student", "email": "student@example.com", "nested": {"grade": "GRADE_7"}}

    assert field_filter.filter_fields(data, fields={"user_id", "name"}) == {"user_id": "user-123", "name": "Student"}
    assert field_filter.filter_fields([data], exclude={"email"}) == [{"user_id": "user-123", "name": "Student", "nested": {"grade": "GRADE_7"}}]
    assert field_filter.parse_fields_query(" user_id, name ,, email ") == {"user_id", "name", "email"}


def test_filterable_response_and_presets():
    response = ExampleResponse(user_id="user-123", name="Student", email="student@example.com")

    assert response.dict_filtered(fields={"user_id", "name"}) == {"user_id": "user-123", "name": "Student"}
    assert field_filter.get_field_set("user_minimal") == {"user_id", "name", "current_grade"}


def test_filterable_response_decorator_handles_sync_and_async():
    @field_filter.filterable_response(default_exclude={"email"})
    def sync_handler(fields=None, exclude=None):
        return {"user_id": "user-123", "name": "Student", "email": "student@example.com"}

    @field_filter.filterable_response()
    async def async_handler(fields=None, exclude=None):
        return {"user_id": "user-123", "name": "Student", "email": "student@example.com"}

    sync_result = sync_handler()
    async_result = asyncio.run(async_handler(fields="user_id,name"))

    assert sync_result == {"user_id": "user-123", "name": "Student"}
    assert async_result == {"user_id": "user-123", "name": "Student"}
