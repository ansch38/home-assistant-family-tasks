from homeassistant.components.sensor import SensorEntity
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    store = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([FamilyCount(store, entry.entry_id, status) for status in ("open", "done", "missed")] + [FamilyCatalog(store, entry.entry_id)])

class FamilyCount(SensorEntity):
    def __init__(self, store, entry_id, status):
        self.store, self.status = store, status
        self._attr_unique_id = f"{entry_id}_{status}"
        self._attr_name = f"Family Tasks {status}"
        self._attr_icon = "mdi:counter"

    async def async_added_to_hass(self):
        self.async_on_remove(self.store.subscribe(self.async_write_ha_state))

    @property
    def native_value(self):
        return sum(i["status"] == self.status for i in self.store.data["instances"])

class FamilyCatalog(SensorEntity):
    _attr_name = "Family Tasks Catalog"
    _attr_icon = "mdi:account-group"
    def __init__(self, store, entry_id):
        self.store = store
        self._attr_unique_id = f"{entry_id}_catalog"
    async def async_added_to_hass(self):
        self.async_on_remove(self.store.subscribe(self.async_write_ha_state))
    @property
    def native_value(self):
        return len(self.store.data["tasks"])
    @property
    def extra_state_attributes(self):
        return {"people": self.store.data["people"], "tasks": self.store.data["tasks"],
                "history": self.store.data["instances"][-500:]}
