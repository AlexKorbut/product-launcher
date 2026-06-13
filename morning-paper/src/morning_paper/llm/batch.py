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
                else:
                    logger.warning("batch item %s failed: %s", custom_id, result.type)
            except Exception as exc:
                logger.warning("batch item %s error: %s", custom_id, exc)

        return results
