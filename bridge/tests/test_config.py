"""Settings loading: environment variables over the `.env` file over defaults."""

from pathlib import Path

import pytest

from bridge.config import DEFAULT_LOG_FILE, Settings, parse_env_file


def test_defaults(tmp_path):
    # An explicitly named missing file is an error (the default repo-root file is optional).
    with pytest.raises(FileNotFoundError):
        Settings.from_env({"BRIDGE_ENV_FILE": str(tmp_path / "missing.env")})
    empty = tmp_path / "empty.env"
    empty.write_text("")
    settings = Settings.from_env({"BRIDGE_ENV_FILE": str(empty)})
    assert settings.upstream == "https://huggingface.co"
    assert settings.public_url == "http://127.0.0.1:8100"
    assert settings.repos == ("Orosius/deltanet-mla-latent",)
    assert settings.tokens == {}
    assert settings.log_file == DEFAULT_LOG_FILE
    assert DEFAULT_LOG_FILE.parts[-4:] == ("harness", "recordings", "raw", "bridge.jsonl")
    assert (settings.host, settings.port) == ("127.0.0.1", 8100)


def test_env_file_is_parsed_and_environment_wins(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# comment\n"
        'HF_OWNER_ACCESS_TOKEN="owner-from-file"\n'
        "\n"
        "export HF_REQUESTER_ACCESS_TOKEN='requester-from-file'\n"
        "HF_REQUESTER_LOGIN=ignored\n"
    )
    assert parse_env_file(env_file)["HF_OWNER_ACCESS_TOKEN"] == "owner-from-file"
    settings = Settings.from_env({"BRIDGE_ENV_FILE": str(env_file), "HF_REQUESTER_ACCESS_TOKEN": "requester-from-env"})
    assert settings.tokens == {"owner": "owner-from-file", "requester": "requester-from-env"}
    assert "owner-from-file" not in repr(settings)


def test_overrides(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("")
    settings = Settings.from_env(
        {
            "BRIDGE_ENV_FILE": str(env_file),
            "BRIDGE_UPSTREAM": "http://127.0.0.1:9999/",
            "BRIDGE_PUBLIC_URL": "http://localhost:8101",
            "BRIDGE_REPOS": " a/b , c/d ",
            "BRIDGE_LOG_FILE": "",
            "BRIDGE_HOST": "0.0.0.0",
            "BRIDGE_PORT": "8101",
        }
    )
    assert settings.upstream == "http://127.0.0.1:9999"
    assert settings.public_url == "http://localhost:8101"
    assert settings.repos == ("a/b", "c/d")
    assert settings.log_file is None
    assert (settings.host, settings.port) == ("0.0.0.0", 8101)
    assert Path(
        Settings.from_env({"BRIDGE_ENV_FILE": str(env_file), "BRIDGE_LOG_FILE": "/tmp/x.jsonl"}).log_file
    ) == Path("/tmp/x.jsonl")


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("BRIDGE_REPOS", ""),
        ("BRIDGE_REPOS", " , "),
        ("BRIDGE_UPSTREAM", "huggingface.co"),
        ("BRIDGE_UPSTREAM", "https://huggingface.co/api"),
    ],
)
def test_invalid_settings_fail_loudly(tmp_path, key, value):
    env_file = tmp_path / ".env"
    env_file.write_text("")
    with pytest.raises(ValueError):
        Settings.from_env({"BRIDGE_ENV_FILE": str(env_file), key: value})
