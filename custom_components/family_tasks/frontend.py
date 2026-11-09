"""Serve a stable card loader and always check the current implementation."""

from hashlib import sha256
from pathlib import Path

from aiohttp import web
from homeassistant.components.http import HomeAssistantView

CARD_URL = "/family_tasks/family-tasks-card.js"
VERSION_URL = "/api/family_tasks/frontend/version"
IMPLEMENTATION_URL = "/api/family_tasks/frontend/card.js"
CACHE_HEADERS = {"Cache-Control": "no-store, max-age=0"}

# Keep this entry point stable. API requests bypass HA's file-cache service
# worker, and the content hash gives each implementation its own module URL.
LOADER = f"""const response = await fetch("{VERSION_URL}", {{cache: "no-store"}});
if (!response.ok) throw new Error("Family Tasks: card version could not be loaded");
const {{version}} = await response.json();
await import("{IMPLEMENTATION_URL}?v=" + encodeURIComponent(version));
"""


class FamilyTasksFrontendView(HomeAssistantView):
    """Expose only bundled JavaScript, never household data."""

    url = CARD_URL
    extra_urls = [VERSION_URL, IMPLEMENTATION_URL]
    name = "family_tasks:frontend"
    requires_auth = False

    def __init__(self, hass):
        self.hass = hass
        self.path = Path(__file__).with_name("family-tasks-card.js")

    async def get(self, request):
        if request.path == CARD_URL:
            return web.Response(
                text=LOADER, content_type="text/javascript", headers=CACHE_HEADERS
            )

        try:
            content = await self.hass.async_add_executor_job(self.path.read_bytes)
        except FileNotFoundError as err:
            raise web.HTTPNotFound(headers=CACHE_HEADERS) from err

        if request.path == VERSION_URL:
            return web.json_response(
                {"version": sha256(content).hexdigest()}, headers=CACHE_HEADERS
            )

        return web.Response(
            body=content, content_type="text/javascript", headers=CACHE_HEADERS
        )

    async def head(self, request):
        return await self.get(request)
