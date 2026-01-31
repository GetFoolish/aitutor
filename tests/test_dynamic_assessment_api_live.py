import os
import sys
from pathlib import Path

# Add project root to path for content module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import requests


DASH_API_URL = os.getenv("DASH_API_URL", "http://localhost:8000")


@pytest.mark.api
@pytest.mark.integration
@pytest.mark.skipif(os.getenv("RUN_LIVE_API_TESTS") != "true", reason="Set RUN_LIVE_API_TESTS=true to run against a live backend")
def test_dynamic_assessment_subjects_no_auth_dev_mode():
    """Integration test that hits a running backend (no FastAPI TestClient).

    This is intentionally minimal: it verifies DEV_MODE auth bypass + subject metadata.
    """

    for subject in ("math", "science", "reading"):
        r = requests.post(
            f"{DASH_API_URL}/api/assessment/dynamic/start",
            json={
                "age_range": "8-10",
                "subject": subject,
                "grade": "3-5",
                "topics": [subject] if subject in {"science", "reading"} else ["math-basics"],
                "question_count": 10,
            },
            timeout=120,
        )
        r.raise_for_status()
        data = r.json()

        assert data.get("assessment_id")
        assert data.get("subject") == subject
        assert isinstance(data.get("questions"), list)
        assert len(data.get("questions")) > 0
        assert data["questions"][0].get("dash_metadata", {}).get("subject") == subject

        assessment_id = data["assessment_id"]
        r2 = requests.get(
            f"{DASH_API_URL}/api/assessment/dynamic/{assessment_id}",
            timeout=120,
        )
        r2.raise_for_status()
        data2 = r2.json()
        assert data2.get("subject") == subject
