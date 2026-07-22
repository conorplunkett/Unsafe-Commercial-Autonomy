from pathlib import Path

from app.env import load_env_file


def _write(tmp_path: Path, text: str) -> Path:
    env_path = tmp_path / ".env"
    env_path.write_text(text, encoding="utf-8")
    return env_path


def test_load_env_file_applies_new_vars(tmp_path, monkeypatch):
    monkeypatch.delenv("PAYBENCH_SKIP_DOTENV", raising=False)
    monkeypatch.delenv("UCA_TEST_ALPHA", raising=False)
    env_path = _write(
        tmp_path,
        """
# comment line
UCA_TEST_ALPHA=one
export UCA_TEST_BETA="quoted value"
UCA_TEST_GAMMA='single'

not a kv line
""",
    )
    monkeypatch.delenv("UCA_TEST_BETA", raising=False)
    monkeypatch.delenv("UCA_TEST_GAMMA", raising=False)

    applied = load_env_file(env_path)

    assert applied == {
        "UCA_TEST_ALPHA": "one",
        "UCA_TEST_BETA": "quoted value",
        "UCA_TEST_GAMMA": "single",
    }
    import os

    assert os.environ["UCA_TEST_BETA"] == "quoted value"


def test_load_env_file_never_overrides_real_environment(tmp_path, monkeypatch):
    monkeypatch.delenv("PAYBENCH_SKIP_DOTENV", raising=False)
    monkeypatch.setenv("UCA_TEST_ALPHA", "from-shell")
    env_path = _write(tmp_path, "UCA_TEST_ALPHA=from-file\n")

    applied = load_env_file(env_path)

    assert applied == {}
    import os

    assert os.environ["UCA_TEST_ALPHA"] == "from-shell"


def test_load_env_file_respects_skip_flag(tmp_path, monkeypatch):
    monkeypatch.setenv("PAYBENCH_SKIP_DOTENV", "1")
    monkeypatch.delenv("UCA_TEST_ALPHA", raising=False)
    env_path = _write(tmp_path, "UCA_TEST_ALPHA=one\n")

    assert load_env_file(env_path) == {}
    import os

    assert "UCA_TEST_ALPHA" not in os.environ


def test_load_env_file_missing_file_is_noop(tmp_path, monkeypatch):
    monkeypatch.delenv("PAYBENCH_SKIP_DOTENV", raising=False)

    assert load_env_file(tmp_path / "nope.env") == {}


def test_load_env_file_skips_empty_template_values(tmp_path, monkeypatch):
    # An unfilled `KEY=` line (as shipped in .env.example) must read as unset.
    monkeypatch.delenv("PAYBENCH_SKIP_DOTENV", raising=False)
    monkeypatch.delenv("UCA_TEST_ALPHA", raising=False)
    env_path = _write(tmp_path, "UCA_TEST_ALPHA=\nUCA_TEST_BETA=real\n")
    monkeypatch.delenv("UCA_TEST_BETA", raising=False)

    applied = load_env_file(env_path)

    assert applied == {"UCA_TEST_BETA": "real"}
    import os

    assert "UCA_TEST_ALPHA" not in os.environ
