"""Opt-in real-browser checks with a simulated HA-style file-cache worker."""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

from test_regressions import INTEGRATION, ROOT, make_hass

ENABLED = (
    os.environ.get("FAMILY_TASKS_BROWSER_TESTS") == "1"
    and importlib.util.find_spec("playwright") is not None
    and importlib.util.find_spec("aiohttp") is not None
)
if ENABLED:
    from aiohttp import web
    from aiohttp.test_utils import TestServer
    from playwright.async_api import async_playwright


# Model the relevant HA rules: API requests use the network, whereas the stable
# resource uses stale-while-revalidate. This is not the full HA service worker.
WORKER = """
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', event => event.waitUntil(self.clients.claim()));
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(fetch(event.request));
  } else if (url.pathname === '/family_tasks/family-tasks-card.js') {
    const fresh = fetch(event.request).then(async response => {
      const cache = await caches.open('test-file-cache');
      if (response.ok) await cache.put(event.request, response.clone());
      return response;
    });
    event.waitUntil(fresh.then(() => {}));
    event.respondWith(caches.open('test-file-cache')
      .then(cache => cache.match(event.request)).then(cached => cached || fresh));
  }
});
"""


@unittest.skipUnless(ENABLED, "Opt in with FAMILY_TASKS_BROWSER_TESTS=1 and install requirements-browser.txt")
class FrontendBrowserTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.folder = tempfile.TemporaryDirectory(prefix="family-tasks-browser-")
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "card.js"
        self.path.write_text('window.familyTasksVersion = "first";', encoding="utf-8")
        self.view = INTEGRATION.FamilyTasksFrontendView(make_hass())
        self.view.path = self.path
        self.requests = []

        async def serve(request):
            self.requests.append(request.path)
            return await self.view.get(request)

        async def index(request):
            return web.Response(text='<!doctype html><html><body></body></html>', content_type="text/html")

        async def worker(request):
            return web.Response(text=WORKER, content_type="text/javascript")

        app = web.Application()
        for url in [self.view.url, *self.view.extra_urls]:
            app.router.add_get(url, serve)
        app.router.add_get('/', index)
        app.router.add_get('/sw.js', worker)
        self.server = TestServer(app)
        self.addAsyncCleanup(self.server.close)
        await self.server.start_server()
        self.playwright = await async_playwright().start()
        self.addAsyncCleanup(self.playwright.stop)
        self.browser = await self.playwright.chromium.launch(
            headless=True, channel=os.environ.get("FAMILY_TASKS_BROWSER_CHANNEL")
        )
        self.addAsyncCleanup(self.browser.close)
        self.page = await self.browser.new_page()
        self.page_errors = []
        self.page.on("pageerror", lambda error: self.page_errors.append(str(error)))
        await self.page.goto(str(self.server.make_url('/')))
        await self.page.evaluate("""async () => {
          await navigator.serviceWorker.register('/sw.js');
          await navigator.serviceWorker.ready;
          if (!navigator.serviceWorker.controller) {
            await new Promise(resolve => navigator.serviceWorker.addEventListener('controllerchange', resolve, {once:true}));
          }
        }""")

    async def load_card(self):
        await self.page.evaluate("""() => new Promise((resolve, reject) => {
          const script = document.createElement('script');
          script.type = 'module';
          script.src = '/family_tasks/family-tasks-card.js';
          script.onload = resolve;
          script.onerror = reject;
          document.body.appendChild(script);
        })""")
        await self.page.wait_for_function('window.familyTasksVersion !== undefined')
        self.assertEqual(self.page_errors, [])

    async def test_cached_loader_loads_updated_real_card_after_normal_reload(self):
        await self.load_card()
        self.assertEqual(await self.page.evaluate('window.familyTasksVersion'), 'first')
        # The worker now has the stable loader cached. Update only the payload.
        self.path.write_text(
            (ROOT / 'family-tasks-card.js').read_text(encoding='utf-8')
            + '\nwindow.familyTasksVersion = "updated";', encoding='utf-8'
        )
        await self.page.reload()
        await self.load_card()
        self.assertEqual(await self.page.evaluate('window.familyTasksVersion'), 'updated')
        self.assertEqual(self.requests.count('/api/family_tasks/frontend/version'), 2)
        self.assertEqual(self.requests.count('/api/family_tasks/frontend/card.js'), 2)
        await self.page.evaluate("""() => {
          const card = document.createElement('family-tasks-board-card');
          card.setConfig({});
          const attributes = {
            today:'2026-11-09', people:[{id:'p',name:'Test'}],
            tasks:[{id:'t',person_id:'p',title:'Overdue'}], history:[],
            current_instances:[{id:'i',task_id:'t',date:'2026-11-01',status:'open'}]
          };
          const hass = {
            states:{'sensor.family_tasks_catalog':{attributes}},
            async callService(domain, service, data) {
              attributes.current_instances[0].status = data.status === 'completed' ? 'done' : 'open';
              card.hass = hass;
            }
          };
          card.hass = hass;
          document.body.appendChild(card);
        }""")
        checkbox = self.page.locator('family-tasks-board-card input[type=checkbox]')
        await checkbox.check()
        self.assertTrue(await checkbox.is_checked())
        self.assertTrue(await checkbox.is_enabled())
        await checkbox.uncheck()
        self.assertFalse(await checkbox.is_checked())

    async def test_old_cached_implementation_requires_one_migration_reload(self):
        await self.page.evaluate("""async () => {
          const cache = await caches.open('test-file-cache');
          await cache.put('/family_tasks/family-tasks-card.js', new Response(
            'window.familyTasksVersion = "legacy";', {headers:{'Content-Type':'text/javascript'}}
          ));
        }""")
        await self.load_card()
        self.assertEqual(await self.page.evaluate('window.familyTasksVersion'), 'legacy')
        await self.page.wait_for_function("""async () => {
          const cache = await caches.open('test-file-cache');
          const response = await cache.match('/family_tasks/family-tasks-card.js');
          return response && (await response.text()).includes('/api/family_tasks/frontend/version');
        }""")
        await self.page.reload()
        await self.load_card()
        self.assertEqual(await self.page.evaluate('window.familyTasksVersion'), 'first')
