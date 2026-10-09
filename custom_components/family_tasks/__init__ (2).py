from datetime import timedelta
import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers import config_validation as cv
from .const import DOMAIN
from .store import FamilyStore
from homeassistant.exceptions import HomeAssistantError
from homeassistant.components.http import StaticPathConfig
from pathlib import Path

PLATFORMS = ["todo", "calendar", "sensor"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    store = FamilyStore(hass)
    await store.load()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = store
    await store.rollover()
    async def tick(now):
        await store.rollover()
    unsub = async_track_time_interval(hass, tick, timedelta(minutes=5))
    entry.async_on_unload(unsub)
    await hass.http.async_register_static_paths([StaticPathConfig(
        "/family_tasks/family-tasks-card.js", str(Path(__file__).parent / "family-tasks-card.js"), False
    )])
    if not hass.services.has_service(DOMAIN, "add_person"):
        async def add_person(call):
            await store.add_person(call.data["name"].strip())
        async def add_task(call):
            person = next((p for p in store.data["people"] if p["name"].casefold() == call.data["person"].strip().casefold()), None)
            if not person:
                raise HomeAssistantError("Person nicht gefunden")
            weekdays = [int(x.strip()) for x in call.data.get("weekdays", "").split(",") if x.strip()]
            if any(x < 0 or x > 6 for x in weekdays):
                raise HomeAssistantError("Wochentage müssen 0 bis 6 sein")
            await store.add_task(call.data["title"].strip(), person["id"], call.data["frequency"],
                                 weekdays, call.data.get("day"), call.data.get("start").isoformat() if call.data.get("start") else None, call.data.get("time_of_day", "anytime"), call.data.get("missed_behavior", "discard"))
        async def update_task(call):
            person = next((p for p in store.data["people"] if p["name"].casefold() == call.data["person"].strip().casefold()), None)
            if not person:
                raise HomeAssistantError("Person nicht gefunden")
            weekdays = [int(x.strip()) for x in call.data.get("weekdays", "").split(",") if x.strip()]
            if any(x < 0 or x > 6 for x in weekdays):
                raise HomeAssistantError("Wochentage müssen 0 bis 6 sein")
            await store.update_task(call.data["task_id"], call.data["title"].strip(), person["id"],
                                    call.data["frequency"], weekdays, call.data.get("day"), call.data.get("time_of_day", "anytime"), call.data.get("missed_behavior", "archive"))
        async def delete_task(call):
            await store.delete_task(call.data["task_id"])
        hass.services.async_register(DOMAIN, "add_person", add_person,
            schema=vol.Schema({vol.Required("name"): cv.string}))
        hass.services.async_register(DOMAIN, "add_task", add_task,
            schema=vol.Schema({vol.Required("title"): cv.string,
                               vol.Required("person"): cv.string,
                               vol.Required("frequency"): vol.In(["daily", "weekly", "monthly"]),
                               vol.Optional("time_of_day", default="anytime"): vol.In(["morning", "daytime", "evening", "anytime"]),
                               vol.Optional("missed_behavior", default="discard"): vol.In(["discard", "archive", "keep"]),
                               vol.Optional("weekdays", default=""): cv.string,
                               vol.Optional("day"): vol.All(vol.Coerce(int), vol.Range(min=1, max=31)),
                               vol.Optional("start"): cv.date}))
        hass.services.async_register(DOMAIN, "update_task", update_task,
            schema=vol.Schema({vol.Required("task_id"): cv.string,
                               vol.Required("title"): cv.string,
                               vol.Required("person"): cv.string,
                               vol.Required("frequency"): vol.In(["daily", "weekly", "monthly"]),
                               vol.Optional("time_of_day", default="anytime"): vol.In(["morning", "daytime", "evening", "anytime"]),
                               vol.Optional("missed_behavior", default="archive"): vol.In(["discard", "archive", "keep"]),
                               vol.Optional("weekdays", default=""): cv.string,
                               vol.Optional("day"): vol.All(vol.Coerce(int), vol.Range(min=1, max=31))}))
        hass.services.async_register(DOMAIN, "delete_task", delete_task,
            schema=vol.Schema({vol.Required("task_id"): cv.string}))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass, entry):
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return ok
