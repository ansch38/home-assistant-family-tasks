"""Dependency-free regression tests; HA boundaries are replaced with test doubles."""

import importlib.util
import sys
import types
import unittest
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch


ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "family_tasks"


class MemoryDisk:
    """Model persistence by copying data, never retaining mutable store references."""

    def __init__(self, hass, version, key):
        self.hass, self.key = hass, key
        self.saves = 0

    async def async_load(self):
        return deepcopy(self.hass.disk.get(self.key))

    async def async_save(self, data):
        self.hass.disk[self.key] = deepcopy(data)
        self.saves += 1


def load_integration():
    """Import real integration source with isolated doubles for external APIs."""
    names = (
        "homeassistant", "homeassistant.core", "homeassistant.config_entries",
        "homeassistant.helpers", "homeassistant.helpers.storage",
        "homeassistant.helpers.event", "homeassistant.helpers.config_validation",
        "homeassistant.util", "homeassistant.exceptions",
        "homeassistant.components", "homeassistant.components.http", "voluptuous",
    )
    modules = {name: types.ModuleType(name) for name in names}
    modules["homeassistant.core"].HomeAssistant = object
    modules["homeassistant.config_entries"].ConfigEntry = object
    modules["homeassistant.helpers.storage"].Store = MemoryDisk
    modules["homeassistant.helpers.event"].async_track_time_interval = (
        lambda hass, callback, interval: hass.track(callback, interval)
    )
    modules["homeassistant.helpers"].config_validation = modules[
        "homeassistant.helpers.config_validation"
    ]
    cv = modules["homeassistant.helpers.config_validation"]
    cv.string, cv.date = str, date
    clock = types.SimpleNamespace(now=lambda: datetime(2026, 11, 4, 12, tzinfo=timezone.utc))
    modules["homeassistant.util"].dt = clock
    modules["homeassistant.exceptions"].HomeAssistantError = ValueError
    modules["homeassistant.components.http"].StaticPathConfig = lambda *args: args
    # Schema validation itself belongs to HA/voluptuous and is not tested here.
    vol = modules["voluptuous"]
    vol.Required = vol.Optional = lambda name, **kwargs: name
    vol.Schema = lambda value: value
    vol.In = vol.All = vol.Coerce = vol.Range = lambda *args, **kwargs: None
    package = "_family_tasks_regression"
    spec = importlib.util.spec_from_file_location(
        package, ROOT / "__init__.py", submodule_search_locations=[str(ROOT)]
    )
    integration = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {**modules, package: integration}):
        try:
            spec.loader.exec_module(integration)
            store_module = sys.modules[f"{package}.store"]
        finally:
            for name in (f"{package}.store", f"{package}.const"):
                sys.modules.pop(name, None)
    return integration, store_module, clock


INTEGRATION, STORE, CLOCK = load_integration()


def make_hass():
    handlers = {}
    services = types.SimpleNamespace(
        has_service=lambda domain, name: (domain, name) in handlers,
        async_register=lambda domain, name, handler, **kwargs: handlers.__setitem__((domain, name), handler),
        async_remove=lambda domain, name: handlers.pop((domain, name)),
    )
    hass = types.SimpleNamespace(
        data={}, disk={}, handlers=handlers, services=services,
        http=types.SimpleNamespace(async_register_static_paths=AsyncMock()),
        config_entries=types.SimpleNamespace(
            async_forward_entry_setups=AsyncMock(),
            async_unload_platforms=AsyncMock(return_value=True),
        ),
        timers=[],
    )

    def track(callback, interval):
        hass.timers.append(callback)
        return lambda: hass.timers.remove(callback)

    hass.track = track
    return hass


class RecurrenceTests(unittest.TestCase):
    def dates(self, frequency, start, end, **kwargs):
        task = dict(start=start, frequency=frequency, weekdays=[], day=1)
        task.update(kwargs)
        return [d.isoformat() for d in STORE.occurrence_dates(
            task, date.fromisoformat(start), date.fromisoformat(end)
        )]

    def test_daily_inclusive_bounds(self):
        self.assertEqual(self.dates("daily", "2026-11-01", "2026-11-03"),
                         ["2026-11-01", "2026-11-02", "2026-11-03"])

    def test_start_anchor_excludes_earlier_dates(self):
        task = dict(start="2026-11-04", frequency="daily")
        self.assertEqual(list(STORE.occurrence_dates(
            task, date(2026, 11, 1), date(2026, 11, 5)
        )), [date(2026, 11, 4), date(2026, 11, 5)])

    def test_weekly_selected_days(self):
        self.assertEqual(self.dates("weekly", "2026-11-01", "2026-11-08", weekdays=[0, 2]),
                         ["2026-11-02", "2026-11-04"])

    def test_month_end_clamping(self):
        self.assertEqual(self.dates("monthly", "2026-01-01", "2026-04-30", day=31),
                         ["2026-01-31", "2026-02-28", "2026-03-31", "2026-04-30"])

    def test_yearly_leap_day(self):
        self.assertEqual(self.dates("yearly", "2024-01-01", "2026-12-31", month=2, day=29),
                         ["2024-02-29", "2025-02-28", "2026-02-28"])


class StoreTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.now = datetime(2026, 11, 4, 12, tzinfo=timezone.utc)
        self.clock_patch = patch.object(CLOCK, "now", lambda: self.now)
        self.clock_patch.start()
        self.addCleanup(self.clock_patch.stop)
        self.hass = make_hass()
        self.store = STORE.FamilyStore(self.hass)
        self.person = await self.store.add_person("Testperson")

    async def task(self, **kwargs):
        return await self.store.add_task("Testaufgabe", self.person["id"],
                                         kwargs.pop("frequency", "daily"), **kwargs)



    async def test_task_due_today_saved_and_notified_once(self):
        listener = Mock()
        self.store.subscribe(listener)
        before = self.store.disk.saves
        task = await self.task()
        self.assertEqual(self.store.disk.saves, before + 1)
        listener.assert_called_once_with()
        saved = self.hass.disk["family_tasks.v1"]
        self.assertEqual(saved["tasks"], [task])
        self.assertEqual(len(saved["instances"]), 1)

    async def test_rollover_and_restart_preserve_instance_ids(self):
        await self.task(start="2026-11-01", missed_behavior="archive")
        expected = deepcopy(self.store.data)
        before = self.store.disk.saves
        await self.store.rollover()
        self.assertEqual(self.store.disk.saves, before)
        restored = STORE.FamilyStore(self.hass)
        await restored.load()
        await restored.rollover()
        self.assertEqual(restored.data, expected)
        keys = [(i["task_id"], i["date"]) for i in restored.data["instances"]]
        self.assertEqual(len(keys), len(set(keys)))

    async def test_discard_removes_overdue_open_but_retains_done(self):
        await self.task()
        first = self.store.data["instances"][0]
        self.now += timedelta(days=1)
        await self.store.rollover()
        self.assertNotIn(first["id"], [i["id"] for i in self.store.data["instances"]])
        second = self.store.data["instances"][0]
        await self.store.complete(second["id"], True)
        self.now += timedelta(days=1)
        await self.store.rollover()
        self.assertEqual(next(i for i in self.store.data["instances"] if i["id"] == second["id"])["status"], "done")

    async def test_archive_marks_old_occurrences_missed(self):
        await self.task(start="2026-11-01", missed_behavior="archive")
        self.assertEqual([i["status"] for i in self.store.data["instances"]],
                         ["missed", "missed", "missed", "open"])
        with self.assertRaises(ValueError):
            await self.store.complete(self.store.data["instances"][0]["id"], True)

    async def test_keep_preserves_one_original_open_instance(self):
        await self.task(start="2026-11-01", missed_behavior="keep")
        original = deepcopy(self.store.data["instances"])
        self.now += timedelta(days=3)
        await self.store.rollover()
        self.assertEqual(self.store.data["instances"], original)
        self.assertEqual(original[0]["date"], "2026-11-01")

    async def test_downtime_backfill_is_bounded(self):
        await self.task(start="2020-01-01", missed_behavior="archive")
        instances = self.store.data["instances"]
        self.assertEqual(len(instances), 367)  # Inclusive: today minus 366 through today.
        self.assertEqual(instances[0]["date"], (self.now.date() - timedelta(days=366)).isoformat())
        self.assertEqual(instances[-1]["status"], "open")

    async def test_keep_overdue_completion_can_be_undone_before_rollover(self):
        await self.task(start="2026-11-01", missed_behavior="keep")
        original = deepcopy(self.store.data["instances"])
        uid = original[0]["id"]
        await self.store.complete(uid, True)
        await self.store.complete(uid, False)
        await self.store.rollover()
        self.assertEqual(self.store.data["instances"], original)

    async def test_complete_and_undo_persist_without_changing_uid(self):
        await self.task()
        instance = self.store.data["instances"][0]
        uid = instance["id"]
        await self.store.complete(uid, True)
        restored = STORE.FamilyStore(self.hass)
        await restored.load()
        self.assertEqual(restored.data["instances"][0]["status"], "done")
        self.assertEqual(restored.data["instances"][0]["completed_at"], self.now.isoformat())
        await restored.complete(uid, False)
        await self.store.load()
        self.assertEqual(self.store.data["instances"][0],
                         dict(id=uid, task_id=instance["task_id"], date="2026-11-04", status="open", completed_at=None))

    async def test_legacy_defaults_preserve_ids_and_history(self):
        await self.task(missed_behavior="archive")
        saved = self.hass.disk["family_tasks.v1"]
        del saved["tasks"][0]["time_of_day"]
        del saved["tasks"][0]["missed_behavior"]
        expected = deepcopy(saved)
        await self.store.load()
        self.assertEqual(self.store.data["instances"], expected["instances"])
        self.assertEqual(self.store.data["tasks"][0]["id"], expected["tasks"][0]["id"])
        self.assertEqual(self.store.data["tasks"][0]["missed_behavior"], "archive")
        self.assertEqual(self.store.data["tasks"][0]["time_of_day"], "anytime")
        before = self.store.disk.saves
        await self.store.load()
        self.assertEqual(self.store.disk.saves, before)


class LifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.hass = make_hass()
        self.cleanup_callbacks = []
        self.entry = types.SimpleNamespace(
            entry_id="test_entry", async_on_unload=self.cleanup_callbacks.append
        )

    async def unload(self):
        ok = await INTEGRATION.async_unload_entry(self.hass, self.entry)
        if ok:
            # HA executes these callbacks after a successful entry unload.
            for callback in self.cleanup_callbacks:
                callback()
            self.cleanup_callbacks.clear()
        return ok

    async def call(self, service, **data):
        await self.hass.handlers[("family_tasks", service)](types.SimpleNamespace(data=data))


    async def test_failed_unload_retains_services_and_store(self):
        await INTEGRATION.async_setup_entry(self.hass, self.entry)
        current = self.hass.data["family_tasks"][self.entry.entry_id]
        self.hass.config_entries.async_unload_platforms.return_value = False
        self.assertFalse(await self.unload())
        self.assertIs(self.hass.data["family_tasks"][self.entry.entry_id], current)
        self.assertEqual(len(self.hass.handlers), 4)
        self.assertEqual(len(self.hass.timers), 1)
        await self.call("add_person", name="Testperson")
        self.assertEqual(len(current.data["people"]), 1)


if __name__ == "__main__":
    unittest.main()
