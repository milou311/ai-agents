from aaos.config.settings import Settings


def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("GROQ_API_KEY", "g")
    monkeypatch.setenv("AAOS_HISTORY_LIMIT", "5")
    s = Settings.from_env()
    assert s.telegram_bot_token == "t"
    assert s.groq_api_key == "g"
    assert s.history_limit == 5
