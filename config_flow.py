import voluptuous as vol
from homeassistant import config_entries
from .const import DOMAIN

class FamilyTasksFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    async def async_step_user(self, user_input=None):
        if user_input is not None:
            await self.async_set_unique_id("family_tasks")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title="Family Tasks", data={})
        return self.async_show_form(step_id="user", data_schema=vol.Schema({}))
