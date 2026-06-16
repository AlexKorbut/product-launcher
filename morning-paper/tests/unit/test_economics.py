"""Cost math for Claude usage."""

from __future__ import annotations

import pytest

from morning_paper.economics import cost_of, estimate_issue_cost


def test_sonnet_full_million():
    # 3.0 in + 15.0 out per 1M.
    assert cost_of("claude-sonnet-4-6", 1_000_000, 1_000_000) == 18.0


def test_haiku_input_only():
    assert cost_of("claude-haiku-4-5", 1_000_000, 0) == 1.0


def test_batch_halves():
    assert cost_of("claude-sonnet-4-6", 1_000_000, 1_000_000, batch=True) == 9.0


def test_cache_read_discount():
    # All input cached -> 10% of input rate, no output.
    assert cost_of("claude-sonnet-4-6", 1_000_000, 0, cached_in=1_000_000) == pytest.approx(0.3)


def test_unknown_model_is_free():
    assert cost_of("gpt-imaginary", 1_000_000, 1_000_000) == 0.0


def test_estimate_in_plausible_range():
    assert 0.0 < estimate_issue_cost() < 5.0
