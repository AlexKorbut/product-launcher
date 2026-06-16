from __future__ import annotations

import logging
import time

from anthropic import Anthropic
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request as BatchRequest

logger = logging.getLogger(__name__)


class BatchProcessor:
    def __init__(self, api_key: str | None = None) -> None:
        self._client = Anthropic(api_key=api_key)

    def run(
        self,
        requests: list[dict],
        *,
        poll_interval_s: float = 5.0,
        timeout_s: float = 600.0,
        usage_ctx: dict | None = None,
        usage_sink=None,
    ) -> dict[str, str]:
        """Submit batch, poll until done, return {custom_id: text_response}."""
        batch_requests: list[BatchRequest] = [
            BatchRequest(
                custom_id=r["custom_id"],
                params=r["params"],
            )
            for r in requests
        ]
        batch = self._client.messages.batches.create(requests=batch_requests)
        batch_id = batch.id

        deadline = time.monotonic() + timeout_s
        while True:
            batch = self._client.messages.batches.retrieve(batch_id)
            if batch.processing_status == "ended":
                break
            if time.monotonic() > deadline:
                logger.warning("batch %s timed out after %.0fs", batch_id, timeout_s)
                break
            time.sleep(poll_interval_s)

        results: dict[str, str] = {}
        for item in self._client.messages.batches.results(batch_id):
            custom_id = item.custom_id
            try:
                result = item.result
                if result.type == "succeeded":
                    for block in result.message.content:
                        if hasattr(block, "text"):
                            results[custom_id] = block.text
                            break
                    if usage_sink is not None and usage_ctx is not None:
                        self._record_usage(result.message, usage_ctx, usage_sink)
                else:
                    logger.warning("batch item %s failed: %s", custom_id, result.type)
            except Exception as exc:
                logger.warning("batch item %s error: %s", custom_id, exc)

        return results

    @staticmethod
    def _record_usage(message, usage_ctx: dict, usage_sink) -> None:
        """Best-effort metering for one succeeded batch item; never raises."""
        try:
            from ..economics import UsageEvent, cost_of

            usage = getattr(message, "usage", None)
            if usage is None:
                return
            tin = getattr(usage, "input_tokens", 0) or 0
            tout = getattr(usage, "output_tokens", 0) or 0
            cin = getattr(usage, "cache_read_input_tokens", 0) or 0
            model = getattr(message, "model", "") or ""
            cost = cost_of(model, tin, tout, cached_in=cin, batch=True)
            usage_sink.record(
                UsageEvent(
                    usage_ctx["user_id"],
                    usage_ctx.get("issue_id"),
                    usage_ctx.get("stage", "editorial"),
                    model,
                    tin,
                    tout,
                    cin,
                    True,
                    cost,
                )
            )
        except Exception:
            pass
