from __future__ import annotations

from app.main import app, frontend_dir


def test_frontend_files_exist() -> None:
    index_file = frontend_dir / "index.html"
    chat_script = frontend_dir / "js" / "chat.js"

    assert index_file.is_file()
    assert chat_script.is_file()
    assert "Avaliação Inicial NR-1" in index_file.read_text(encoding="utf-8")
    assert 'id="finishButton"' in index_file.read_text(encoding="utf-8")
    assert "createSession" in chat_script.read_text(encoding="utf-8")
    assert "onFinish" in chat_script.read_text(encoding="utf-8")


def test_root_route_is_registered() -> None:
    assert any(getattr(route, "path", None) == "/" for route in app.routes)
