"""Enrichment task scheduling from sync handlers."""

from __future__ import annotations

import asyncio
import threading
import time

import pytest

from app.services.artwork_enrichment import bind_app_event_loop, schedule_artwork_enrichment


@pytest.mark.asyncio
async def test_schedule_from_async_context_uses_running_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    scheduled: list[int] = []

    async def fake_run(artwork_id: int) -> None:
        scheduled.append(artwork_id)

    monkeypatch.setattr("app.services.artwork_enrichment._run_enrichment_task", fake_run)

    schedule_artwork_enrichment(42)
    await asyncio.sleep(0)

    assert scheduled == [42]


def test_schedule_from_sync_thread_uses_bound_app_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    scheduled: list[int] = []

    async def fake_run(artwork_id: int) -> None:
        scheduled.append(artwork_id)

    monkeypatch.setattr("app.services.artwork_enrichment._run_enrichment_task", fake_run)

    def fail_asyncio_run(_coro):
        raise AssertionError("asyncio.run must not be used for enrichment scheduling")

    monkeypatch.setattr("asyncio.run", fail_asyncio_run)

    loop = asyncio.new_event_loop()

    def run_loop() -> None:
        asyncio.set_event_loop(loop)
        loop.run_forever()

    server = threading.Thread(target=run_loop, name="test-asgi-loop", daemon=True)
    bind_app_event_loop(loop)
    server.start()

    try:
        schedule_artwork_enrichment(7)

        deadline = time.time() + 2
        while not scheduled and time.time() < deadline:
            time.sleep(0.01)
    finally:
        loop.call_soon_threadsafe(loop.stop)
        server.join(timeout=1)

    assert scheduled == [7]
