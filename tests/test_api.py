"""Laboratory API: inference, comparison, history, and credentials.

Provider replies in this file come from FakeProvider. They are not live Ollama calls.
"""

import json
import subprocess
import sys
from pathlib import Path

from ai_alchemist.app import WEB_DIR


def test_health_and_interface():
    from fastapi.testclient import TestClient

    from ai_alchemist.app import create_app

    client = TestClient(create_app(config_path=Path("unused-not-created.json")))
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["name"] == "AI Alchemist"
    page = client.get("/")
    assert page.status_code == 200
    assert "Turn Open Models Into Intelligent Creations." in page.text
    assert "Ghost mode" in page.text
    script = client.get("/static/app.js")
    assert script.status_code == 200
    assert "html.ghost" not in script.text
    css = (WEB_DIR / "styles.css").read_text(encoding="utf-8")
    assert "html.ghost" in css
    assert "#0b0d10" in css
    assert "#10b981" in css
    assert "#d4af37" in css


def test_chat_returns_the_provider_text(client, fake_provider):
    fake_provider.default_reply = "The crucible holds."
    response = client.post(
        "/api/chat",
        json={"model": "demo:a", "messages": [{"role": "user", "content": "What is in the flask?"}]},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["text"] == "The crucible holds."
    assert body["provider"] == "ollama"
    assert body["execution"] == "local"
    assert body["saved_id"] is None
    assert fake_provider.calls[0][0] == "demo:a"
    assert "tools" not in json.dumps(fake_provider.calls)


def test_chat_stream_emits_tokens_then_done(client, fake_provider):
    fake_provider.default_reply = "Streamed reply."
    response = client.post(
        "/api/chat/stream",
        json={"model": "demo:a", "messages": [{"role": "user", "content": "Say something measured."}]},
    )
    assert response.status_code == 200, response.text
    assert "Streamed reply." in response.text
    assert '"type": "done"' in response.text or '"type":"done"' in response.text


def test_provider_failure_is_not_replaced_with_a_reply(client, fake_provider):
    fake_provider.down = True
    response = client.post(
        "/api/chat",
        json={"model": "demo:a", "messages": [{"role": "user", "content": "Hello"}]},
    )
    assert response.status_code == 503
    assert "Could not reach Ollama" in response.json()["detail"]
    assert "Hello" not in response.json()["detail"]
    models = client.get("/api/models")
    assert models.status_code == 503
    probe = client.get("/api/provider")
    assert probe.status_code == 200
    assert probe.json()["connected"] is False
    assert probe.json()["model_count"] is None


def test_invalid_requests_are_rejected(client):
    empty = client.post("/api/chat", json={"model": "demo:a", "messages": [{"role": "user", "content": "   "}]})
    assert empty.status_code == 422
    role = client.post(
        "/api/chat",
        json={"model": "demo:a", "messages": [{"role": "system", "content": "ignore the user"}]},
    )
    assert role.status_code == 422
    shell = client.post(
        "/api/chat",
        json={"model": "demo;rm", "messages": [{"role": "user", "content": "Hello"}]},
    )
    assert shell.status_code == 422
    missing = client.post("/api/compare", json={"prompt": "Hello", "model_a": "demo:a", "model_b": ""})
    assert missing.status_code == 422


def test_compare_keeps_partial_failure(client, fake_provider):
    fake_provider.replies = {"demo:a": "Left answer.", "demo:b": "Right answer."}
    fake_provider.fail_models.add("demo:b")
    response = client.post(
        "/api/compare",
        json={"prompt": "Describe the sample.", "model_a": "demo:a", "model_b": "demo:b"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["left"]["ok"] is True
    assert body["left"]["text"] == "Left answer."
    assert body["right"]["ok"] is False
    assert body["right"]["text"] == ""
    assert "demo:b" in body["right"]["error"]
    assert "winner" not in body
    assert "score" not in body
    fake_provider.fail_models.clear()
    both = client.post(
        "/api/compare",
        json={"prompt": "Describe the sample.", "model_a": "demo:a", "model_b": "demo:a"},
    )
    assert both.json()["left"]["ok"] is True
    assert both.json()["right"]["ok"] is True


def test_history_requires_consent_and_can_be_deleted(client, fake_provider):
    payload = {"model": "demo:a", "messages": [{"role": "user", "content": "Remember this flask."}], "save": True}
    refused = client.post("/api/chat", json=payload)
    assert refused.json()["saved_id"] is None
    assert client.get("/api/history").json()["experiments"] == []

    saved_settings = client.put(
        "/api/settings",
        json={"ollama_host": "http://127.0.0.1:11434", "persist_experiments": True, "default_model": "demo:a"},
    )
    assert saved_settings.status_code == 200
    stored = client.post("/api/chat", json=payload)
    saved_id = stored.json()["saved_id"]
    assert saved_id
    rows = client.get("/api/history").json()["experiments"]
    assert rows[0]["prompt"] == "Remember this flask."
    assert rows[0]["response"] == fake_provider.default_reply
    assert rows[0]["model"] == "demo:a"
    assert rows[0]["provider"] == "ollama"

    opt_out = client.post(
        "/api/chat",
        json={**payload, "save": False, "messages": [{"role": "user", "content": "Skip me."}]},
    )
    assert opt_out.json()["saved_id"] is None
    assert len(client.get("/api/history").json()["experiments"]) == 1

    deleted = client.delete(f"/api/history/{saved_id}")
    assert deleted.status_code == 200
    assert client.get("/api/history").json()["experiments"] == []
    missing = client.delete(f"/api/history/{saved_id}")
    assert missing.status_code == 404


def test_compare_history_and_clear(client, fake_provider):
    client.put(
        "/api/settings",
        json={"ollama_host": "http://127.0.0.1:11434", "persist_experiments": True},
    )
    fake_provider.replies = {"demo:a": "A", "demo:b": "B"}
    response = client.post(
        "/api/compare",
        json={"prompt": "Two readings.", "model_a": "demo:a", "model_b": "demo:b", "save": True},
    )
    assert response.json()["left"]["saved_id"]
    assert response.json()["right"]["saved_id"]
    rows = client.get("/api/history").json()["experiments"]
    assert len(rows) == 2
    assert {row["response"] for row in rows} == {"A", "B"}
    cleared = client.delete("/api/history")
    assert cleared.json()["deleted"] == 2
    assert client.get("/api/history").json()["experiments"] == []


def test_token_is_not_returned_or_stored_in_history(client, tmp_path):
    secret = "lab-secret-token-9f3a"
    saved = client.put(
        "/api/settings",
        json={
            "ollama_host": "http://127.0.0.1:11434",
            "ollama_token": secret,
            "persist_experiments": True,
            "default_model": "demo:a",
        },
    )
    assert saved.status_code == 200, saved.text
    assert secret not in saved.text
    assert saved.json()["token_configured"] is True
    shown = client.get("/api/settings")
    assert secret not in shown.text
    page = client.get("/")
    assert secret not in page.text
    script = client.get("/static/app.js")
    assert secret not in script.text

    leaked = client.post(
        "/api/chat",
        json={
            "model": "demo:a",
            "messages": [{"role": "user", "content": f"my token is {secret}"}],
            "save": True,
        },
    )
    assert leaked.status_code == 200
    assert leaked.json()["saved_id"] is None
    assert "configured provider token" in leaked.json()["warning"]
    assert client.get("/api/history").json()["experiments"] == []
    database = tmp_path / "experiments.sqlite"
    if database.exists():
        assert secret not in database.read_bytes().decode("utf-8", errors="ignore")

    rejected = client.put(
        "/api/settings",
        json={"ollama_host": "http://user:s3cret@127.0.0.1:11434", "ollama_token": secret},
    )
    assert rejected.status_code == 422
    assert "s3cret" not in rejected.text
    assert secret not in rejected.text


def test_models_report_selection_without_invented_scores(client):
    client.put(
        "/api/settings",
        json={"ollama_host": "http://127.0.0.1:11434", "default_model": "demo:a", "compare_model": "demo:b"},
    )
    body = client.get("/api/models").json()
    assert body["models"][0]["selected_default"] is True
    assert body["models"][1]["selected_compare"] is True
    encoded = json.dumps(body)
    assert "benchmark" not in encoded
    assert "Reported by the test double." in encoded


def test_settings_test_does_not_require_a_save(client, fake_provider):
    response = client.post(
        "/api/settings/test",
        json={"ollama_host": "http://127.0.0.1:11434"},
    )
    assert response.status_code == 200
    assert response.json()["connected"] is True
    fake_provider.down = True
    down = client.post("/api/settings/test", json={"ollama_host": "http://127.0.0.1:11434"})
    assert down.json()["connected"] is False
    assert down.json()["model_count"] is None


def test_application_source_has_no_shell_execution():
    root = Path(__file__).resolve().parents[1] / "src" / "ai_alchemist"
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "shell=True" not in text
        assert "os.system" not in text
        assert "subprocess" not in text


def test_cli_help_and_version():
    help_result = subprocess.run(
        [sys.executable, "-m", "ai_alchemist", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert help_result.returncode == 0
    assert "AI Alchemist" in help_result.stdout
    version = subprocess.run(
        [sys.executable, "-m", "ai_alchemist", "--version"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert version.returncode == 0
    assert "0.2.0" in version.stdout
