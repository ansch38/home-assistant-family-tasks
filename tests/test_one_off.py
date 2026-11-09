"""One-off lifecycle tests using synthetic data and a controlled HA-local clock."""

import unittest
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from unittest.mock import Mock, patch

from test_regressions import CALENDAR, CLOCK, INTEGRATION, SENSOR, STORE, TODO, make_hass, real_vol


class OneOffTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.now = datetime(2026, 11, 9, 12, tzinfo=timezone(timedelta(hours=1)))
        clock_patch = patch.object(CLOCK, "now", lambda: self.now)
        clock_patch.start()
        self.addCleanup(clock_patch.stop)
        self.hass = make_hass()
        self.store = STORE.FamilyStore(self.hass)
        self.person = await self.store.add_person("Testperson")

    async def add(self, start="2026-11-09", **kwargs):
        return await self.store.add_task("One-off", self.person["id"], "once", start=start, **kwargs)

    async def update(self, task, **kwargs):
        return await self.store.update_task(task["id"], "Edited", self.person["id"], "once", **kwargs)

    def view_ids(self):
        attrs = SENSOR.FamilyCatalog(self.store, "entry").extra_state_attributes
        ids = [i["id"] for i in attrs["current_instances"]]
        self.assertEqual(ids, [i.uid for i in TODO.FamilyTodo(self.store, "entry").todo_items])
        return ids

    async def restore(self):
        restored = STORE.FamilyStore(self.hass)
        await restored.load()
        await restored.rollover()
        self.store = restored

    async def test_today_creates_one_instance_with_keep_default(self):
        task = await self.add()
        self.assertEqual(task["missed_behavior"], "keep")
        self.assertEqual(len(self.store.data["instances"]), 1)
        instance = self.store.data["instances"][0]
        self.assertEqual(instance["id"], task["once_instance_id"])
        self.assertEqual(instance["date"], "2026-11-09")
        self.assertEqual(self.view_ids(), [instance["id"]])
        self.assertEqual(TODO.FamilyTodo(self.store, "entry").todo_items[0].description, "Einmalige Familienaufgabe")

    async def test_far_future_is_persisted_and_visible_as_one_calendar_event(self):
        task = await self.add("2040-02-29")
        self.assertEqual(self.view_ids(), [])
        self.assertEqual(self.store.data["instances"], [])
        await self.restore()
        self.assertEqual(self.store.data["tasks"][0], task)
        calendar = CALENDAR.FamilyCalendar(self.store, "entry")
        events = calendar._events(date(2026, 1, 1), date(2050, 12, 31))
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].start, date(2040, 2, 29))
        self.assertEqual(events[0].end, date(2040, 3, 1))
        self.assertEqual(events[0].uid, task["once_instance_id"])
        self.assertEqual(calendar.event.start, date(2040, 2, 29))

    async def test_invalid_or_missing_dates_do_not_mutate_store(self):
        before = deepcopy(self.store.data)
        for value in (None, "", "2026-02-29", "2026-13-01", "2026-11-09T12:00:00Z", "20261109", "2026-W46-1", 123):
            with self.subTest(value=value), self.assertRaises(ValueError):
                await self.add(value)
            self.assertEqual(self.store.data, before)

    async def test_invalid_edit_does_not_partially_change_title_or_due_date(self):
        task = await self.add()
        before = deepcopy(self.store.data)
        with self.assertRaises(ValueError):
            await self.update(task, start="invalid")
        self.assertEqual(self.store.data, before)

    async def test_long_past_dates_honor_each_missed_behavior(self):
        for behavior, expected in (("keep", "open"), ("archive", "missed"), ("discard", None)):
            task = await self.add("2020-01-01", missed_behavior=behavior)
            instances = [i for i in self.store.data["instances"] if i["task_id"] == task["id"]]
            self.assertEqual([i["status"] for i in instances], [expected] if expected else [])
            if instances:
                self.assertEqual(instances[0]["date"], "2020-01-01")
            for _ in range(3):
                await self.store.rollover()
            await self.restore()
            after = [i for i in self.store.data["instances"] if i["task_id"] == task["id"]]
            self.assertEqual(after, instances)
            self.assertTrue(any(t["id"] == task["id"] for t in self.store.data["tasks"]))

    async def test_aging_today_applies_keep_archive_and_discard(self):
        tasks = {behavior: await self.add(missed_behavior=behavior) for behavior in ("keep", "archive", "discard")}
        self.now += timedelta(days=500)
        await self.restore()
        for behavior, status in (("keep", "open"), ("archive", "missed"), ("discard", None)):
            items = [i for i in self.store.data["instances"] if i["task_id"] == tasks[behavior]["id"]]
            self.assertEqual([i["status"] for i in items], [status] if status else [])

    async def test_completion_undo_and_next_day_never_create_follow_up(self):
        await self.add("2026-11-01")
        original = deepcopy(self.store.data["instances"][0])
        uid = original["id"]
        await self.store.complete(uid, True)
        self.assertEqual(self.view_ids(), [uid])
        await self.store.rollover()
        await self.store.complete(uid, False)
        self.assertEqual(self.view_ids(), [uid])
        await self.store.complete(uid, True)
        self.now += timedelta(days=2)
        await self.restore()
        self.assertEqual(self.view_ids(), [])
        self.assertEqual(len(self.store.data["instances"]), 1)
        self.assertEqual(self.store.data["instances"][0]["id"], uid)
        self.assertEqual(self.store.data["instances"][0]["status"], "done")

    async def test_calendar_end_is_exclusive_and_once_never_repeats(self):
        await self.add("2028-02-29")
        calendar = CALENDAR.FamilyCalendar(self.store, "entry")
        before = await calendar.async_get_events(self.hass, datetime(2028, 2, 28), datetime(2028, 2, 29))
        on_day = await calendar.async_get_events(self.hass, datetime(2028, 2, 29), datetime(2028, 3, 1))
        after = calendar._events(date(2028, 3, 1), date(2050, 12, 31))
        self.assertEqual(before, [])
        self.assertEqual(len(on_day), 1)
        self.assertEqual(after, [])

    async def test_explicit_reschedule_after_discard_reuses_reserved_identity(self):
        task = await self.add(missed_behavior="discard")
        uid = task["once_instance_id"]
        self.now += timedelta(days=1)
        await self.store.rollover()
        self.assertEqual(self.store.data["instances"], [])
        await self.store.rollover()
        self.assertEqual(self.store.data["instances"], [])
        await self.update(task, start=self.store.today)
        self.assertEqual(self.view_ids(), [uid])
        await self.restore()
        self.assertEqual(len(self.store.data["instances"]), 1)

    async def test_move_future_to_today_to_future_and_past_keeps_uid(self):
        task = await self.add("2026-12-01")
        uid = task["once_instance_id"]
        listener = Mock()
        self.store.subscribe(listener)
        await self.update(task, start="2026-11-09")
        self.assertEqual(self.view_ids(), [uid])
        listener.assert_called_once_with()
        await self.update(task, start="2027-01-01")
        self.assertEqual(self.view_ids(), [])
        self.assertEqual(self.store.data["instances"][0]["date"], "2027-01-01")
        await self.store.rollover()
        self.assertEqual(len(self.store.data["instances"]), 1)
        await self.update(task, start="2026-10-01")
        self.assertEqual(self.view_ids(), [uid])
        self.assertEqual(self.store.data["instances"][0]["date"], "2026-10-01")
        await self.restore()
        self.assertEqual(self.store.data["instances"][0]["id"], uid)
        event = CALENDAR.FamilyCalendar(self.store, "entry")._events(date(2026, 1, 1), date(2027, 12, 31))[0]
        self.assertEqual(event.start, date(2026, 10, 1))
        self.assertEqual(event.uid, uid)

    async def test_rescheduling_into_past_applies_archive_and_discard_immediately(self):
        for behavior, expected in (("archive", "missed"), ("discard", None)):
            task = await self.add("2026-12-01", missed_behavior=behavior)
            await self.update(task, start="2026-11-09")
            uid = next(i["id"] for i in self.store.data["instances"] if i["task_id"] == task["id"])
            await self.update(task, start="2026-11-01")
            items = [i for i in self.store.data["instances"] if i["task_id"] == task["id"]]
            self.assertEqual([i["status"] for i in items], [expected] if expected else [])
            self.assertNotIn(uid, self.view_ids())
            if items:
                self.assertEqual(items[0]["id"], uid)

    async def test_completed_and_archived_dates_are_locked_even_outside_history_window(self):
        done = await self.add()
        await self.store.complete(self.store.data["instances"][0]["id"], True)
        missed = await self.add("2020-01-01", missed_behavior="archive")
        # Force the target instances out of the catalog history window.
        self.store.data["instances"].extend(dict(id=f"filler-{i}", task_id="deleted", date="2020-01-01", status="missed") for i in range(501))
        for task in (done, missed):
            before = deepcopy(self.store.data)
            with self.assertRaises(ValueError):
                await self.update(task, start="2027-01-01")
            self.assertEqual(self.store.data, before)
            attrs = SENSOR.FamilyCatalog(self.store, "entry").extra_state_attributes
            self.assertTrue(next(t for t in attrs["tasks"] if t["id"] == task["id"])["date_locked"])
            await self.update(task)

    async def test_switching_once_and_recurring_is_rejected_before_mutation(self):
        once = await self.add()
        recurring = await self.store.add_task("Daily", self.person["id"], "daily")
        for task, target in ((once, "daily"), (recurring, "once")):
            before = deepcopy(self.store.data)
            with self.assertRaises(ValueError):
                await self.store.update_task(task["id"], "Changed", self.person["id"], target, start="2026-11-09")
            self.assertEqual(self.store.data, before)
        with self.assertRaises(ValueError):
            await self.store.update_task(recurring["id"], "Changed", self.person["id"], "daily", start="2026-12-01")

    async def test_delete_retains_history_without_recreating_task(self):
        task = await self.add()
        history = deepcopy(self.store.data["instances"])
        await self.store.delete_task(task["id"])
        await self.restore()
        self.assertEqual(self.store.data["instances"], history)
        self.assertEqual(self.view_ids(), [])
        self.assertEqual(CALENDAR.FamilyCalendar(self.store, "entry")._events(date(2026, 1, 1), date(2027, 1, 1)), [])

    async def test_separate_same_named_tasks_are_allowed_and_recurring_defaults_unchanged(self):
        first, second = await self.add(), await self.add()
        self.assertNotEqual(first["id"], second["id"])
        self.assertNotEqual(first["once_instance_id"], second["once_instance_id"])
        daily = await self.store.add_task("Daily", self.person["id"], "daily")
        self.assertEqual(daily["missed_behavior"], "discard")
        self.assertNotIn("once_instance_id", daily)
        await self.store.update_task(daily["id"], "Daily", self.person["id"], "daily")
        self.assertEqual(daily["missed_behavior"], "archive")

    async def test_local_calendar_date_not_utc_date_controls_fulfillment(self):
        self.now = datetime(2026, 11, 9, 0, 15, tzinfo=timezone(timedelta(hours=1)))
        self.assertEqual(self.now.astimezone(timezone.utc).date(), date(2026, 11, 8))
        task = await self.add("2026-11-09")
        self.assertEqual(self.view_ids(), [task["once_instance_id"]])
        future = await self.add("2026-11-10")
        self.assertNotIn(future["once_instance_id"], self.view_ids())


@unittest.skipIf(real_vol is None, "Install tests/requirements.txt for actual service-schema checks")
class OneOffServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.hass = make_hass()
        self.callbacks = []
        from types import SimpleNamespace
        self.entry = SimpleNamespace(entry_id="entry", async_on_unload=self.callbacks.append)
        await INTEGRATION.async_setup_entry(self.hass, self.entry)
        self.store = self.hass.data["family_tasks"]["entry"]
        await self.call("add_person", name="Testperson")

    async def call(self, service, **data):
        from types import SimpleNamespace
        data = self.hass.schemas[("family_tasks", service)](data)
        await self.hass.handlers[("family_tasks", service)](SimpleNamespace(data=data))

    async def test_service_creates_and_moves_once_with_real_schema(self):
        await self.call("add_task", title="Service once", person="Testperson", frequency="once", start="2040-02-29")
        task = self.store.data["tasks"][0]
        self.assertEqual(task["missed_behavior"], "keep")
        await self.call("update_task", task_id=task["id"], title="Due now", person="Testperson", frequency="once", start=self.store.today)
        self.assertEqual(self.store.current_instances()[0]["id"], task["once_instance_id"])
        await self.call("update_task", task_id=task["id"], title="Renamed", person="Testperson", frequency="once")
        self.assertEqual(task["missed_behavior"], "keep")

    async def test_service_rejects_missing_and_invalid_date_without_mutation(self):
        for payload in ({}, {"start": "bad"}, {"start": "2026-02-29"}, {"start": "2026-11-09T00:00:00Z"}):
            before = deepcopy(self.store.data)
            with self.subTest(payload=payload), self.assertRaises((ValueError, real_vol.Invalid)):
                await self.call("add_task", title="Invalid", person="Testperson", frequency="once", **payload)
            self.assertEqual(self.store.data, before)

    async def test_explicit_missed_behavior_survives_updates_and_reload(self):
        await self.call("add_task", title="Archive", person="Testperson", frequency="once", start="2040-01-01", missed_behavior="archive")
        task = self.store.data["tasks"][0]
        await self.call("update_task", task_id=task["id"], title="Updated", person="Testperson", frequency="once")
        self.assertEqual(task["missed_behavior"], "archive")
        await INTEGRATION.async_unload_entry(self.hass, self.entry)
        for callback in self.callbacks:
            callback()
        self.callbacks.clear()
        await INTEGRATION.async_setup_entry(self.hass, self.entry)
        restored = self.hass.data["family_tasks"]["entry"]
        self.assertEqual(restored.data["tasks"][0], task)

    async def test_service_blocks_type_switch(self):
        await self.call("add_task", title="Recurring", person="Testperson", frequency="weekly", weekdays="0")
        task = self.store.data["tasks"][0]
        with self.assertRaises(ValueError):
            await self.call("update_task", task_id=task["id"], title="Changed", person="Testperson", frequency="once", start="2040-01-01")
