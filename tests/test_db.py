import os
import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("CI") == "true", reason="Skip DB tests on CI unless Mongo is available"
)


def test_connection_and_indexes():
    from src.dash_system.db import ensure_indexes, get_collections

    ensure_indexes()
    skills, questions, users = get_collections()
    assert skills is not None
    assert questions is not None
    assert users is not None
