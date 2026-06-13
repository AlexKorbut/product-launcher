"""Usage metering repository round-trips against an isolated SQLite database."""

from __future__ import annotations

import pytest

pytest.importorskip("sqlalchemy")

from morning_paper.db import get_engine, init_db  # noqa: E402
from morning_paper.db.repository import (  # noqa: E402
    issue_cost,
    record_usage,
    user_usage,
)


@pytest.fixture()
def engine(tmp_path):
    eng = get_engine(f"sqlite:///{tmp_path / 'test.db'}")
    init_db(eng)
    return eng


def _seed(engine):
    # issue A: two events across two stages.
    record_usage(
        user_id="u1", issue_id="A", stage="profile", model="claude-haiku-4-5",
        tokens_in=1000, tokens_out=200, cost_usd=0.10, engine=engine,
    )
    record_usage(
        user_id="u1", issue_id="A", stage="editorial", model="claude-sonnet-4-6",
        tokens_in=2000, tokens_out=500, batch=True, cost_usd=0.25, engine=engine,
    )
    # issue B: one event.
    record_usage(
        user_id="u1", issue_id="B", stage="editorial", model="claude-sonnet-4-6",
        tokens_in=3000, tokens_out=700, cost_usd=0.40, engine=engine,
    )


def test_issue_cost_sums_and_breaks_down(engine):
    _seed(engine)
    res = issue_cost("A", engine=engine)
    assert res["cost_usd"] == pytest.approx(0.35)
    assert res["tokens_in"] == 3000
    assert res["tokens_out"] == 700
    assert len(res["events"]) == 2
    stages = {e["stage"] for e in res["events"]}
    assert stages == {"profile", "editorial"}


def test_issue_cost_no_rows(engine):
    res = issue_cost("missing", engine=engine)
    assert res["cost_usd"] == 0.0
    assert res["tokens_in"] == 0
    assert res["tokens_out"] == 0
    assert res["events"] == []


def test_user_usage_aggregates(engine):
    _seed(engine)
    res = user_usage("u1", engine=engine)
    assert res["cost_usd"] == pytest.approx(0.75)
    assert res["tokens_in"] == 6000
    assert res["tokens_out"] == 1400
    assert res["issues"] == 2


def test_user_usage_empty(engine):
    res = user_usage("nobody", engine=engine)
    assert res["cost_usd"] == 0.0
    assert res["issues"] == 0
