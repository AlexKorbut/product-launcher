"""Repository round-trips against an isolated SQLite database."""

from __future__ import annotations

import pytest

pytest.importorskip("sqlalchemy")

from morning_paper.db import (  # noqa: E402
    get_engine,
    get_source_accounts,
    init_db,
    load_profile,
    save_profile,
    save_signals,
    upsert_source_account,
    upsert_user,
)
from morning_paper.models import InterestProfile, Signal, SignalKind  # noqa: E402


@pytest.fixture()
def engine(tmp_path):
    eng = get_engine(f"sqlite:///{tmp_path / 'test.db'}")
    init_db(eng)
    return eng


def test_upsert_user_idempotent(engine):
    upsert_user("u1", engine=engine)
    upsert_user("u1", output_lang="en", engine=engine)  # no error on repeat


def test_save_signals_dedup(engine):
    upsert_user("u1", engine=engine)
    sig = Signal.make(
        user_id="u1", source_id="rss", kind=SignalKind.READ, text="hello", external_id="x1"
    )
    dup = Signal.make(
        user_id="u1", source_id="rss", kind=SignalKind.READ, text="hello", external_id="x1"
    )
    assert sig.id == dup.id
    n1 = save_signals([sig, dup], engine=engine)
    assert n1 == 1
    n2 = save_signals([dup], engine=engine)
    assert n2 == 0


def test_private_signal_text_blanked(engine):
    upsert_user("u1", engine=engine)
    sig = Signal.make(
        user_id="u1",
        source_id="tg",
        kind=SignalKind.MESSAGE,
        text="secret",
        external_id="m1",
        is_private=True,
    )
    save_signals([sig], engine=engine)
    from morning_paper.db.schema import SignalRow
    from morning_paper.db import get_session

    with get_session(engine=engine) as s:
        row = s.get(SignalRow, sig.id)
        assert row.is_private is True
        assert row.text == ""


def test_profile_roundtrip(engine):
    upsert_user("u1", engine=engine)
    profile = InterestProfile(
        user_id="u1",
        output_lang="ru",
        topics={"tech/ai": 0.9, "sports": 0.2},
        entities={"OpenAI": 0.7},
        interest_vectors=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
        version=2,
    )
    save_profile(profile, engine=engine)
    loaded = load_profile("u1", engine=engine)
    assert loaded is not None
    assert loaded.topics == {"tech/ai": 0.9, "sports": 0.2}
    assert loaded.entities == {"OpenAI": 0.7}
    assert loaded.version == 2
    assert loaded.interest_vectors == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]

    # Re-save replaces vectors, not appends.
    profile.interest_vectors = [[1.0, 1.0, 1.0]]
    save_profile(profile, engine=engine)
    reloaded = load_profile("u1", engine=engine)
    assert reloaded.interest_vectors == [[1.0, 1.0, 1.0]]


def test_load_profile_missing(engine):
    assert load_profile("nobody", engine=engine) is None


def test_source_account_roundtrip(engine):
    upsert_user("u1", engine=engine)
    upsert_source_account(
        "u1", "rss", options={"feeds": ["https://example.com/rss"]}, secret_ref="ref1", engine=engine
    )
    accounts = get_source_accounts("u1", engine=engine)
    assert len(accounts) == 1
    acc = accounts[0]
    assert acc["source_id"] == "rss"
    assert acc["options"] == {"feeds": ["https://example.com/rss"]}
    assert acc["secret_ref"] == "ref1"
    assert acc["enabled"] is True
    assert acc["cursor"] is None

    # Upsert again updates in place.
    upsert_source_account("u1", "rss", options={"feeds": []}, enabled=False, engine=engine)
    accounts = get_source_accounts("u1", engine=engine)
    assert len(accounts) == 1
    assert accounts[0]["options"] == {"feeds": []}
    assert accounts[0]["enabled"] is False
