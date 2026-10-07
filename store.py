from datetime import date, timedelta
from calendar import monthrange
from uuid import uuid4
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

def occurrence_dates(task, start, end):
    anchor = date.fromisoformat(task["start"])
    current = max(anchor, start)
    while current <= end:
        freq = task["frequency"]
        match = (freq == "daily" or
                 freq == "weekly" and current.weekday() in task["weekdays"] or
                 freq == "monthly" and current.day == min(task["day"], monthrange(current.year, current.month)[1]))
        if match:
            yield current
        current += timedelta(days=1)

class FamilyStore:
    def __init__(self, hass):
        self.hass = hass
        self.disk = Store(hass, 1, "family_tasks.v1")
        self.data = {"people": [], "tasks": [], "instances": []}
        self.listeners = set()

    async def load(self):
        self.data = await self.disk.async_load() or self.data
        changed = False
        for task in self.data.get("tasks", []):
            if "time_of_day" not in task:
                task["time_of_day"] = "anytime"
                changed = True
        if changed:
            await self.disk.async_save(self.data)

    async def save(self):
        await self.disk.async_save(self.data)
        for callback in tuple(self.listeners):
            callback()

    def subscribe(self, callback):
        self.listeners.add(callback)
        return lambda: self.listeners.discard(callback)

    async def add_person(self, name):
        if any(p["name"].casefold() == name.casefold() for p in self.data["people"]):
            raise ValueError("Person existiert bereits")
        person = {"id": uuid4().hex, "name": name}
        self.data["people"].append(person)
        await self.save()
        return person

    async def add_task(self, title, person_id, frequency, weekdays=None, day=None, start=None, time_of_day="anytime"):
        if not any(p["id"] == person_id for p in self.data["people"]):
            raise ValueError("Unbekannte Person")
        task = {"id": uuid4().hex, "title": title, "person_id": person_id,
                "frequency": frequency, "weekdays": weekdays or [],
                "day": day or 1, "start": start or dt_util.now().date().isoformat(),
                "time_of_day": time_of_day}
        self.data["tasks"].append(task)
        await self.rollover()
        return task

    async def rollover(self):
        today = dt_util.now().date()
        changed = False
        for instance in self.data["instances"]:
            if instance["status"] == "open" and instance["date"] < today.isoformat():
                instance["status"] = "missed"
                changed = True
        existing = {(i["task_id"], i["date"]) for i in self.data["instances"]}
        for task in self.data["tasks"]:
            anchor = date.fromisoformat(task["start"])
            # Backfill at most 366 days after downtime; no duplicates.
            begin = max(anchor, today - timedelta(days=366))
            for due in occurrence_dates(task, begin, today):
                key = (task["id"], due.isoformat())
                if key not in existing:
                    self.data["instances"].append({
                        "id": uuid4().hex, "task_id": task["id"], "date": due.isoformat(),
                        "status": "open" if due == today else "missed",
                        "completed_at": None})
                    existing.add(key)
                    changed = True
        if changed:
            await self.save()

    async def complete(self, uid, completed):
        instance = next((i for i in self.data["instances"] if i["id"] == uid), None)
        if not instance or instance["status"] == "missed":
            raise ValueError("Aufgabe nicht verfügbar oder bereits archiviert")
        instance["status"] = "done" if completed else "open"
        instance["completed_at"] = dt_util.now().isoformat() if completed else None
        await self.save()

    async def update_task(self, task_id, title, person_id, frequency, weekdays=None, day=None, time_of_day="anytime"):
        task = next((t for t in self.data["tasks"] if t["id"] == task_id), None)
        if task is None:
            raise ValueError("Aufgabe nicht gefunden")
        if not any(p["id"] == person_id for p in self.data["people"]):
            raise ValueError("Person nicht gefunden")
        task.update(title=title, person_id=person_id, frequency=frequency,
                    weekdays=weekdays or [], day=day or 1, time_of_day=time_of_day)
        # Already recorded occurrences remain historical. Only future instances
        # follow the changed recurrence; today's existing instance remains.
        await self.save()
        return task

    async def delete_task(self, task_id):
        self.data["tasks"] = [t for t in self.data["tasks"] if t["id"] != task_id]
        # Instances deliberately retained for historical reporting.
        await self.save()

    def person_name(self, pid):
        return next((p["name"] for p in self.data["people"] if p["id"] == pid), "?")
