"""Tests for V2.0 Lifecycle manager."""

import asyncio
import pytest
from backend.lifecycle.manager import LifecycleManager
from backend.config.settings import Settings


@pytest.fixture
def lifecycle():
    return LifecycleManager(settings=Settings())


class TestLifecycleManager:
    def test_initial_health(self, lifecycle):
        h = lifecycle.health()
        assert h["status"] == "stopped"
        assert h["version"] == "2.0"

    def test_register_component(self, lifecycle):
        lifecycle.register_component("camera", "ready")
        h = lifecycle.health()
        assert h["components"]["camera"] == "ready"

    def test_update_component(self, lifecycle):
        lifecycle.register_component("camera", "registered")
        lifecycle.update_component("camera", "active")
        h = lifecycle.health()
        assert h["components"]["camera"] == "active"

    def test_startup_sets_running(self, lifecycle):
        asyncio.get_event_loop().run_until_complete(lifecycle.startup())
        assert lifecycle.is_running is True

    def test_shutdown_clears_running(self, lifecycle):
        asyncio.get_event_loop().run_until_complete(lifecycle.startup())
        asyncio.get_event_loop().run_until_complete(lifecycle.shutdown())
        assert lifecycle.is_running is False

    def test_startup_hook_called(self, lifecycle):
        called = []
        lifecycle.on_startup(lambda: called.append(1))
        asyncio.get_event_loop().run_until_complete(lifecycle.startup())
        assert called == [1]

    def test_shutdown_hook_called(self, lifecycle):
        called = []
        lifecycle.on_shutdown(lambda: called.append(1))
        asyncio.get_event_loop().run_until_complete(lifecycle.startup())
        asyncio.get_event_loop().run_until_complete(lifecycle.shutdown())
        assert called == [1]

    def test_uptime_when_stopped(self, lifecycle):
        assert lifecycle.uptime == 0.0

    def test_uptime_when_started(self, lifecycle):
        asyncio.get_event_loop().run_until_complete(lifecycle.startup())
        assert lifecycle.uptime >= 0.0

    def test_startup_hook_failure_doesnt_crash(self, lifecycle):
        def bad_hook():
            raise RuntimeError("boom")
        lifecycle.on_startup(bad_hook)
        asyncio.get_event_loop().run_until_complete(lifecycle.startup())
        assert lifecycle.is_running is True

    def test_shutdown_hook_failure_doesnt_crash(self, lifecycle):
        def bad_hook():
            raise RuntimeError("boom")
        lifecycle.on_shutdown(bad_hook)
        asyncio.get_event_loop().run_until_complete(lifecycle.startup())
        asyncio.get_event_loop().run_until_complete(lifecycle.shutdown())
        assert lifecycle.is_running is False
