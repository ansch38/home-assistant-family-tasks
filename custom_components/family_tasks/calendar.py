from datetime import date, timedelta
from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.util import dt as dt_util
from .const import DOMAIN
from .store import occurrence_dates

async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([FamilyCalendar(hass.data[DOMAIN][entry.entry_id], entry.entry_id)])

class FamilyCalendar(CalendarEntity):
    _attr_name = "Family Tasks"
    _attr_icon = "mdi:calendar-check"

    def __init__(self, store, entry_id):
        self.store = store
        self._attr_unique_id = f"{entry_id}_calendar"

    async def async_added_to_hass(self):
        self.async_on_remove(self.store.subscribe(self._changed))

    def _changed(self):
        self.async_write_ha_state()
        self.async_update_event_listeners()

    @property
    def event(self):
        today = dt_util.now().date()
        events = self._events(today, today + timedelta(days=90))
        # A single date can lie beyond the recurring calendar's lookahead.
        for task in self.store.data["tasks"]:
            if task["frequency"] == "once":
                due = date.fromisoformat(task["start"])
                if due > today + timedelta(days=90):
                    events.extend(self._events(due, due, [task]))
        return next((e for e in sorted(events, key=lambda e: (e.start, e.summary)) if e.end > today), None)

    def _events(self, start, end, tasks=None):
        statuses = {(i["task_id"], i["date"]): i["status"] for i in self.store.data["instances"]}
        result = []
        today = dt_util.now().date()
        for task in self.store.data["tasks"] if tasks is None else tasks:
            for due in occurrence_dates(task, start, end):
                status = statuses.get((task["id"], due.isoformat()))
                if status is None and due < today and task.get("missed_behavior") == "discard":
                    continue
                status = status or "planned"
                prefix = {"done": "✓ ", "missed": "✗ "}.get(status, "")
                result.append(CalendarEvent(
                    start=due, end=due + timedelta(days=1),
                    summary=f'{prefix}{self.store.person_name(task["person_id"])}: {task["title"]}',
                    description=f"Status: {status}",
                    uid=task.get("once_instance_id", task["id"]) if task["frequency"] == "once" else f'{task["id"]}:{due.isoformat()}'))
        return sorted(result, key=lambda e: (e.start, e.summary))

    async def async_get_events(self, hass, start_date, end_date):
        # Calendar end bound is exclusive.
        return self._events(start_date.date(), (end_date - timedelta(microseconds=1)).date())
