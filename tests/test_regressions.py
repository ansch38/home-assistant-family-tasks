"""Dependency-free regression tests; HA boundaries are replaced with test doubles."""

import importlib.util
import asyncio
import sys
import types
import unittest
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

try:
    import voluptuous as real_vol
except ImportError:
    real_vol = None

try:
    import aiohttp
    # Load its classes before patch.dict restores sys.modules; otherwise a
    # later HTTP test could import a second, incompatible Application class.
    from aiohttp import web
except ImportError:
    aiohttp = None


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
        "homeassistant.components.sensor", "homeassistant.components.todo",
        "homeassistant.components.calendar",
        "homeassistant.helpers.entity",
    )
    modules = {name: types.ModuleType(name) for name in names}
    if aiohttp is None:
        modules["aiohttp"] = types.ModuleType("aiohttp")
        modules["aiohttp"].web = types.SimpleNamespace()
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
    cv.string = str
    def calendar_date(value):
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if not isinstance(value, str) or len(value) != 10:
            raise ValueError("Expected a calendar date")
        return date.fromisoformat(value)
    cv.date = calendar_date
    clock = types.SimpleNamespace(now=lambda: datetime(2026, 11, 4, 12, tzinfo=timezone.utc))
    modules["homeassistant.util"].dt = clock
    modules["homeassistant.exceptions"].HomeAssistantError = ValueError
    modules["homeassistant.components.http"].HomeAssistantView = object
    modules["homeassistant.components.sensor"].SensorEntity = object
    modules["homeassistant.helpers.entity"].Entity = object
    todo = modules["homeassistant.components.todo"]
    todo.TodoListEntity = object
    todo.TodoItem = types.SimpleNamespace
    todo.TodoItemStatus = types.SimpleNamespace(COMPLETED="completed", NEEDS_ACTION="needs_action")
    todo.TodoListEntityFeature = types.SimpleNamespace(UPDATE_TODO_ITEM=1)
    calendar = modules["homeassistant.components.calendar"]
    calendar.CalendarEntity = object
    calendar.CalendarEvent = types.SimpleNamespace
    # Without the optional dependency, exercise handlers without schema checks.
    vol = modules["voluptuous"]
    vol.Required = vol.Optional = lambda name, **kwargs: name
    vol.Schema = lambda value: value
    vol.In = vol.All = vol.Coerce = vol.Range = lambda *args, **kwargs: None
    if real_vol is not None:
        modules["voluptuous"] = real_vol
    package = "_family_tasks_regression"
    spec = importlib.util.spec_from_file_location(
        package, ROOT / "__init__.py", submodule_search_locations=[str(ROOT)]
    )
    integration = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {**modules, package: integration}):
        try:
            spec.loader.exec_module(integration)
            store_module = sys.modules[f"{package}.store"]
            sensor_module = importlib.import_module(f"{package}.sensor")
            todo_module = importlib.import_module(f"{package}.todo")
            calendar_module = importlib.import_module(f"{package}.calendar")
        finally:
            for name in (f"{package}.store", f"{package}.const", f"{package}.sensor", f"{package}.todo", f"{package}.calendar", f"{package}.frontend"):
                sys.modules.pop(name, None)
    return integration, store_module, clock, sensor_module, todo_module, calendar_module


INTEGRATION, STORE, CLOCK, SENSOR, TODO, CALENDAR = load_integration()


def make_hass():
    handlers = {}
    schemas = {}

    def register(domain, name, handler, **kwargs):
        handlers[(domain, name)] = handler
        schemas[(domain, name)] = kwargs["schema"]

    services = types.SimpleNamespace(
        has_service=lambda domain, name: (domain, name) in handlers,
        async_register=register,
        async_remove=lambda domain, name: handlers.pop((domain, name)),
    )
    hass = types.SimpleNamespace(
        data={}, disk={}, handlers=handlers, schemas=schemas, services=services,
        http=types.SimpleNamespace(register_view=Mock()),
        async_add_executor_job=AsyncMock(side_effect=asyncio.to_thread),
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

    async def test_future_task_persisted_and_notified_without_instances(self):
        listener = Mock()
        self.store.subscribe(listener)
        task = await self.task(start="2026-12-01")
        restored = STORE.FamilyStore(self.hass)
        await restored.load()
        self.assertEqual(restored.data["tasks"], [task])
        self.assertEqual(restored.data["instances"], [])
        listener.assert_called_once_with()

    async def test_weekly_task_not_due_today_survives_reload(self):
        task = await self.task(frequency="weekly", weekdays=[0])
        restored = STORE.FamilyStore(self.hass)
        await restored.load()
        self.assertEqual(restored.data["tasks"], [task])
        self.assertEqual(restored.data["instances"], [])

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


class CurrentViewTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = StoreTests.asyncSetUp
    task = StoreTests.task

    def assert_views(self, expected_ids):
        catalog = SENSOR.FamilyCatalog(self.store, "test_entry")
        todo = TODO.FamilyTodo(self.store, "test_entry")
        attributes = catalog.extra_state_attributes
        self.assertEqual(attributes["today"], self.now.date().isoformat())
        self.assertEqual([i["id"] for i in attributes["current_instances"]], expected_ids)
        self.assertEqual([i.uid for i in todo.todo_items], expected_ids)
        return attributes, todo

    async def test_catalog_and_todo_select_same_current_instances(self):
        task = await self.task()
        def instance(uid, due, status, completed_at=None, task_id=task["id"]):
            return dict(id=uid, task_id=task_id, date=due, status=status, completed_at=completed_at)
        self.store.data["instances"] = [
            instance("today_open", "2026-11-04", "open"),
            instance("today_done", "2026-11-04", "done", "2026-11-04T10:00:00+00:00"),
            instance("overdue", "2026-10-01", "open"),
            instance("overdue_done_today", "2026-10-01", "done", "2026-11-04T10:00:00+00:00"),
            instance("old_done", "2026-10-01", "done", "2026-11-03T10:00:00+00:00"),
            instance("missed", "2026-11-04", "missed"),
            instance("future", "2026-11-05", "open"),
            instance("deleted_task", "2026-11-04", "open", task_id="deleted"),
        ]
        self.assert_views(["today_open", "today_done", "overdue", "overdue_done_today"])

    async def test_old_open_instance_outside_history_limit_remains_actionable(self):
        task = await self.task(start="2026-01-01", missed_behavior="keep")
        oldest = deepcopy(self.store.data["instances"][0])
        self.store.data["instances"].extend(
            dict(id=f"history-{index}", task_id=task["id"], date="2026-10-01", status="done", completed_at="2026-10-01T12:00:00+00:00")
            for index in range(600)
        )
        attributes, _ = self.assert_views([oldest["id"]])
        self.assertEqual(len(attributes["history"]), 500)
        self.assertNotIn(oldest, attributes["history"])
        attributes["current_instances"][0]["status"] = "done"
        self.assertEqual(self.store.data["instances"][0]["status"], "open")

    async def test_overdue_completion_and_undo_retain_same_uid_in_both_views(self):
        await self.task(start="2026-11-01", missed_behavior="keep")
        uid = self.store.data["instances"][0]["id"]
        await self.store.complete(uid, True)
        attributes, todo = self.assert_views([uid])
        self.assertEqual(attributes["current_instances"][0]["status"], "done")
        self.assertEqual(todo.todo_items[0].status, "completed")
        await todo.async_update_todo_item(types.SimpleNamespace(uid=uid, status="needs_action"))
        attributes, _ = self.assert_views([uid])
        self.assertEqual(attributes["current_instances"][0]["status"], "open")

    async def test_midnight_notifies_without_disk_changes_and_expires_done_items(self):
        # Annual task has no next-day occurrence to force a save/notification.
        await self.task(frequency="yearly", month=11, day=4)
        uid = self.store.data["instances"][0]["id"]
        await self.store.complete(uid, True)
        self.assert_views([uid])
        listener = Mock()
        self.store.subscribe(listener)
        saves = self.store.disk.saves
        self.now += timedelta(days=1)
        self.assertFalse(await self.store.rollover())
        listener.assert_called_once_with()
        self.assertEqual(self.store.disk.saves, saves)
        self.assert_views([])
        await self.store.rollover()
        listener.assert_called_once_with()

    async def test_midnight_refreshes_empty_catalog(self):
        listener = Mock()
        self.store.subscribe(listener)
        self.now += timedelta(days=1)
        await self.store.rollover()
        listener.assert_called_once_with()
        self.assert_views([])

    async def test_home_assistant_day_can_differ_from_utc_day(self):
        self.now = datetime(2026, 11, 5, 0, 15, tzinfo=timezone(timedelta(hours=1)))
        self.assertEqual(self.now.astimezone(timezone.utc).date(), date(2026, 11, 4))
        await self.task()
        uid = self.store.data["instances"][0]["id"]
        self.assert_views([uid])
        await self.store.complete(uid, True)
        self.assert_views([uid])


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
        if real_vol is not None:
            data = self.hass.schemas[("family_tasks", service)](data)
        await self.hass.handlers[("family_tasks", service)](types.SimpleNamespace(data=data))

    @unittest.skipIf(real_vol is None, "Install tests/requirements.txt for real service-schema validation")
    async def test_yearly_edit_accepts_month_and_preserves_recorded_instances(self):
        await INTEGRATION.async_setup_entry(self.hass, self.entry)
        await self.call("add_person", name="Testperson")
        await self.call("add_task", title="Yearly", person="Testperson", frequency="yearly", month=11, day=4)
        store = self.hass.data["family_tasks"][self.entry.entry_id]
        task_id = store.data["tasks"][0]["id"]
        history = deepcopy(store.data["instances"])
        await self.call("update_task", task_id=task_id, title="Yearly edited", person="Testperson", frequency="yearly", month=2, day=29)
        restored = STORE.FamilyStore(self.hass)
        await restored.load()
        task = restored.data["tasks"][0]
        self.assertEqual((task["id"], task["month"], task["day"]), (task_id, 2, 29))
        self.assertEqual(restored.data["instances"], history)
        self.assertEqual(list(STORE.occurrence_dates(task, date(2027, 1, 1), date(2027, 12, 31))), [date(2027, 2, 28)])
        for month in (0, 13):
            with self.assertRaises(real_vol.Invalid):
                await self.call("update_task", task_id=task_id, title="Invalid", person="Testperson", frequency="yearly", month=month)

    async def test_reload_services_use_current_store(self):
        await INTEGRATION.async_setup_entry(self.hass, self.entry)
        await self.call("add_person", name="Testperson")
        old = self.hass.data["family_tasks"][self.entry.entry_id]
        self.assertTrue(await self.unload())
        self.assertEqual(self.hass.handlers, {})
        self.assertEqual(self.hass.timers, [])
        await INTEGRATION.async_setup_entry(self.hass, self.entry)
        current = self.hass.data["family_tasks"][self.entry.entry_id]
        self.assertIsNot(current, old)
        old_data = deepcopy(old.data)
        await self.call("add_person", name="Weitere Testperson")
        await self.call("add_task", title="Test", person="Testperson", frequency="daily")
        task_id = current.data["tasks"][0]["id"]
        await self.call("update_task", task_id=task_id, title="Geaendert", person="Testperson", frequency="daily")
        self.assertEqual(current.data["tasks"][0]["title"], "Geaendert")
        await self.call("delete_task", task_id=task_id)
        self.assertEqual(current.data["tasks"], [])
        self.assertEqual(len(current.data["people"]), 2)
        self.assertEqual(old.data, old_data)
        self.assertEqual(len(self.hass.timers), 1)
        self.hass.http.register_view.assert_called_once()
        view = self.hass.http.register_view.call_args.args[0]
        self.assertEqual(view.url, "/family_tasks/family-tasks-card.js")
        self.assertFalse(view.requires_auth)

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
