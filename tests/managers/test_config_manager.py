import json

import pytest

from managers.config_manager import ConfigManager


def test_config_manager_reads_env_and_updates_config(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "llm_models": {
                    "chat": {"model": "gpt-4o-mini"},
                },
                "api_endpoints": {
                    "openrouter": "https://openrouter.ai/api/v1",
                    "google": "https://generativelanguage.googleapis.com",
                },
            }
        )
    )

    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-key")
    monkeypatch.setenv("GOOGLE_API_KEY", "google-key")

    manager = ConfigManager(str(config_path))

    assert manager.get_api_key("openrouter") == "openrouter-key"
    assert manager.get_api_key("google") == "google-key"
    assert manager.get_llm_config("chat") == {"model": "gpt-4o-mini"}
    assert manager.get_api_endpoint("google") == "https://generativelanguage.googleapis.com"

    manager.update_model("chat", "gpt-4o")

    saved = json.loads(config_path.read_text())
    assert saved["llm_models"]["chat"]["model"] == "gpt-4o"

    with pytest.raises(ValueError, match="Unknown provider"):
        manager.get_api_key("missing")
    with pytest.raises(ValueError, match="Unknown use case"):
        manager.get_llm_config("missing")
    with pytest.raises(ValueError, match="Unknown provider"):
        manager.get_api_endpoint("missing")
