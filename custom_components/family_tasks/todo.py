from datetime import date
from homeassistant.util import dt as dt_util
from homeassistant.components.todo import TodoListEntity, TodoItem, TodoItemStatus, TodoListEntityFeature
from homeassistant.helpers.entity import Entity
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    store = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([FamilyTodo(store, entry.entry_id)])

class FamilyTodo(TodoListEntity):
    _attr_name = "Family Tasks"
    _attr_icon = "mdi:format-list-checks"
    _attr_supported_features = TodoListEntityFeature.UPDATE_TODO_ITEM

    def __init__(self, store, entry_id):
        self.store = store
        self._attr_unique_id = f"{entry_id}_todo"

    async def async_added_to_hass(self):
        self.async_on_remove(self.store.subscribe(self.async_write_ha_state))

    @property
    def todo_items(self):
        tasks = {t["id"]: t for t in self.store.data["tasks"]}
        return [
            TodoItem(uid=i["id"],
                     summary=f'{self.store.person_name(tasks[i["task_id"]]["person_id"])}: {tasks[i["task_id"]]["title"]}',
                     status=TodoItemStatus.COMPLETED if i["status"] == "done" else TodoItemStatus.NEEDS_ACTION,
                     due=date.fromisoformat(i["date"]),
                     description="Wiederkehrende Familienaufgabe")
            for i in self.store.data["instances"]
            if i["status"] in ("open", "done") and i["task_id"] in tasks
            and (
                i["date"] == dt_util.now().date().isoformat()
                or (i["status"] == "open" and i["date"] < dt_util.now().date().isoformat())
                # A previously overdue item completed today must remain in
                # the To-do entity for the rest of the day. Otherwise HA
                # rejects undoing completion because its UID vanished.
                or (
                    i["status"] == "done"
                    and i["date"] < dt_util.now().date().isoformat()
                    and (i.get("completed_at") or "")[:10] == dt_util.now().date().isoformat()
                )
            )
        ]

    async def async_update_todo_item(self, item):
        await self.store.complete(item.uid, item.status == TodoItemStatus.COMPLETED)
