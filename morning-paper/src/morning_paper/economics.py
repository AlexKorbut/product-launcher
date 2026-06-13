"""Pricing + cost math for Claude API usage. Pure stdlib."""

from __future__ import annotations

from dataclasses import dataclass

# USD per 1M tokens: (input, output), keyed by model id.
PRICES: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5": (1.0, 5.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-opus-4-8": (5.0, 25.0),
}


def cost_of(
    model: str,
    tokens_in: int,
    tokens_out: int,
    *,
    batch: bool = False,
    cached_in: int = 0,
) -> float:
    """Dollar cost of one call. Cache reads -90%, Batch -50%. Unknown model -> 0.0."""
    in_rate, out_rate = PRICES.get(model, (0.0, 0.0))
    non_cached = max(tokens_in - cached_in, 0)
    input_cost = non_cached / 1e6 * in_rate + cached_in / 1e6 * in_rate * 0.10
    output_cost = tokens_out / 1e6 * out_rate
    total = input_cost + output_cost
    if batch:
        total *= 0.5
    return total


@dataclass
class UsageEvent:
    user_id: str
    issue_id: str | None
    stage: str
    model: str
    tokens_in: int
    tokens_out: int
    cached_in: int = 0
    batch: bool = False
    cost_usd: float = 0.0


def estimate_issue_cost(
    *,
    n_signals: int = 300,
    n_stories: int = 30,
    batch: bool = True,
    cache: bool = True,
) -> float:
    """Back-of-envelope per-issue cost against the $0.10-0.50 target.

    Rough constants (documented here, not load-bearing):
      - tagging: n_signals items batched on Haiku, ~120 in + ~40 out tokens each
      - summarize+translate: n_stories on Sonnet, ~700 in + ~450 out each
      - editorial: ~5 Opus calls, ~2500 in + ~900 out each
      - grid: 1 Opus call, ~3000 in + ~800 out
    Haiku+Sonnet use `batch` pricing; Opus is non-batch. If `cache`, treat ~50% of
    Opus/Sonnet input as cache reads. Sanity estimate only.
    """
    from .llm.models import HAIKU, OPUS, SONNET

    total = 0.0

    # Tagging on Haiku (batched).
    tag_in = n_signals * 120
    tag_out = n_signals * 40
    total += cost_of(HAIKU, tag_in, tag_out, batch=batch)

    # Summarize + translate on Sonnet (batched).
    sum_in = n_stories * 700
    sum_out = n_stories * 450
    sum_cached = sum_in // 2 if cache else 0
    total += cost_of(SONNET, sum_in, sum_out, batch=batch, cached_in=sum_cached)

    # Editorial: ~5 Opus calls (non-batch).
    ed_in = 5 * 2500
    ed_out = 5 * 900
    ed_cached = ed_in // 2 if cache else 0
    total += cost_of(OPUS, ed_in, ed_out, cached_in=ed_cached)

    # Grid: 1 Opus call (non-batch).
    grid_in = 3000
    grid_out = 800
    grid_cached = grid_in // 2 if cache else 0
    total += cost_of(OPUS, grid_in, grid_out, cached_in=grid_cached)

    return total
