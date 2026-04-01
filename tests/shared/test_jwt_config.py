import pytest

import shared.jwt_config as jwt_config


def test_validate_jwt_secret_checks_basic_requirements():
    assert jwt_config.validate_jwt_secret("secret") == (
        False,
        "JWT_SECRET is using a known weak/default value: 'secret'",
    )
    assert jwt_config.validate_jwt_secret("letters-only-secret-without-digits-abcdef") == (
        False,
        "JWT_SECRET should contain both letters and numbers for better security",
    )

    valid, error = jwt_config.validate_jwt_secret("StrongSecret1234567890abcdefghijklmnopqrstuvwxyz")
    assert valid is True
    assert error == ""


def test_should_fail_closed_on_weak_jwt_secret_in_deployed_runtimes(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.delenv("K_SERVICE", raising=False)
    assert jwt_config.should_fail_closed_on_weak_jwt_secret() is True

    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("K_SERVICE", "auth-service")
    assert jwt_config.should_fail_closed_on_weak_jwt_secret() is True

    monkeypatch.delenv("K_SERVICE", raising=False)
    assert jwt_config.should_fail_closed_on_weak_jwt_secret() is False


def test_handle_invalid_jwt_secret_exits_when_fail_closed(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.delenv("K_SERVICE", raising=False)

    with pytest.raises(SystemExit):
        jwt_config.handle_invalid_jwt_secret("bad secret")


def test_handle_invalid_jwt_secret_warns_in_development(monkeypatch, capsys):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("K_SERVICE", raising=False)

    jwt_config.handle_invalid_jwt_secret("bad secret")

    output = capsys.readouterr().out
    assert "JWT SECURITY ERROR" in output
    assert "WARNING: Running in development mode with weak JWT secret" in output
