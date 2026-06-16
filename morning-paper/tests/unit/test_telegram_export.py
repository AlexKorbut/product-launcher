import json

from morning_paper.models import SignalKind
from morning_paper.sources.base import AuthState, SourceConfig
from morning_paper.sources.telegram_export import TelegramExportSource, _flatten_text

_AUTH = AuthState(source_id="telegram_export", user_id="u", status="connected")


def _export():
    return {
        "chats": {
            "list": [
                {
                    "name": "Cool Tech Channel",
                    "type": "public_channel",
                    "id": 111,
                    "messages": [
                        {
                            "id": 1,
                            "type": "message",
                            "date": "2026-01-01T10:00:00",
                            "text": "A public post about Rust",
                        },
                        {
                            "id": 2,
                            "type": "message",
                            "date": "2026-01-02T10:00:00",
                            "forwarded_from": "Some Author",
                            "text": ["Forwarded ", {"type": "bold", "text": "insight"}],
                        },
                    ],
                },
                {
                    "name": "Alice",
                    "type": "personal_chat",
                    "id": 222,
                    "messages": [
                        {
                            "id": 5,
                            "type": "message",
                            "date": "2026-01-03T10:00:00",
                            "text": "private secret plans",
                        },
                        {"id": 6, "type": "service", "text": "joined"},
                    ],
                },
            ]
        }
    }


def _write(tmp_path, data):
    path = tmp_path / "result.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


def _cfg(path, **opts):
    return SourceConfig(
        source_id="telegram_export", user_id="u", options={"path": path, **opts}
    )


def test_flatten_text_handles_list_of_parts():
    assert _flatten_text("plain") == "plain"
    assert _flatten_text(["a ", {"type": "bold", "text": "b"}, "c"]) == "a bc"
    assert _flatten_text([{"no_text_key": 1}]) == ""


def test_public_channel_subscription_and_forward(tmp_path):
    path = _write(tmp_path, _export())
    src = TelegramExportSource()
    result = src.fetch(_cfg(path), _AUTH, cursor=None)

    subs = [s for s in result.signals if s.kind == SignalKind.SUBSCRIPTION]
    forwards = [s for s in result.signals if s.kind == SignalKind.FORWARD]

    assert any(s.text == "Cool Tech Channel" for s in subs)
    assert len(forwards) == 1
    assert forwards[0].text == "Forwarded insight"
    assert "Some Author" in forwards[0].entities_hint


def test_private_skipped_unless_included(tmp_path):
    path = _write(tmp_path, _export())
    src = TelegramExportSource()

    excluded = src.fetch(_cfg(path, include_private=False), _AUTH, cursor=None)
    assert not any(
        s.kind == SignalKind.MESSAGE and "private" in s.text for s in excluded.signals
    )

    included = src.fetch(_cfg(path, include_private=True), _AUTH, cursor=None)
    private_msgs = [
        s
        for s in included.signals
        if s.kind == SignalKind.MESSAGE and "private" in s.text
    ]
    assert len(private_msgs) == 1
    assert private_msgs[0].is_private is True
    assert private_msgs[0].raw_ref is None


def test_cursor_returned(tmp_path):
    path = _write(tmp_path, _export())
    src = TelegramExportSource()
    result = src.fetch(_cfg(path, include_private=True), _AUTH, cursor=None)
    assert result.cursor is not None
