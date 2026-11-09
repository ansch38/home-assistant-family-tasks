"""Exercise the real aiohttp responses; the HA view base is a test double."""

import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path

from test_regressions import INTEGRATION, make_hass

HAS_AIOHTTP = importlib.util.find_spec("aiohttp") is not None
if HAS_AIOHTTP:
    from aiohttp import web
    from aiohttp.test_utils import TestClient, TestServer


@unittest.skipUnless(HAS_AIOHTTP, "Install tests/requirements.txt for real HTTP tests")
class FrontendHTTPTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.folder = tempfile.TemporaryDirectory(prefix="family-tasks-http-")
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "card.js"
        self.path.write_bytes(b'window.familyTasksVersion = "first";')
        self.hass = make_hass()
        self.view = INTEGRATION.FamilyTasksFrontendView(self.hass)
        self.view.path = self.path
        app = web.Application()
        for url in [self.view.url, *self.view.extra_urls]:
            app.router.add_get(url, self.view.get)
        self.client = TestClient(TestServer(app))
        self.addAsyncCleanup(self.client.close)
        await self.client.start_server()

    def assert_no_cache(self, response):
        self.assertEqual(response.headers["Cache-Control"], "no-store, max-age=0")

    async def test_stable_url_returns_loader_not_cached_implementation(self):
        for suffix in ("", "?v=20261108"):
            response = await self.client.get(self.view.url + suffix)
            self.assertEqual(response.status, 200)
            self.assert_no_cache(response)
            self.assertEqual(response.content_type, "text/javascript")
            loader = await response.text()
            self.assertIn('/api/family_tasks/frontend/version', loader)
            self.assertIn('cache: "no-store"', loader)
            self.assertIn('await import(', loader)
            self.assertNotIn('window.familyTasksVersion', loader)

    async def test_version_is_hash_of_served_content_and_changes_on_update(self):
        first = await self.client.get('/api/family_tasks/frontend/version')
        self.assert_no_cache(first)
        version = (await first.json())["version"]
        self.assertEqual(version, hashlib.sha256(self.path.read_bytes()).hexdigest())
        code = await self.client.get('/api/family_tasks/frontend/card.js?v=' + version)
        self.assert_no_cache(code)
        self.assertEqual(code.content_type, "text/javascript")
        self.assertEqual(await code.read(), self.path.read_bytes())

        # Preserve both size and mtime: content hashing must still detect change.
        import os
        stamp = self.path.stat()
        self.path.write_bytes(b'window.familyTasksVersion = "other";')
        os.utime(self.path, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        updated = await self.client.get('/api/family_tasks/frontend/version')
        new_version = (await updated.json())["version"]
        self.assertNotEqual(version, new_version)
        updated_code = await self.client.get('/api/family_tasks/frontend/card.js?v=' + new_version)
        self.assertEqual(await updated_code.read(), self.path.read_bytes())
        self.assertGreaterEqual(self.hass.async_add_executor_job.await_count, 4)

    async def test_old_conditional_headers_cannot_hide_updated_code(self):
        self.path.write_bytes(b'window.familyTasksVersion = "other";')
        response = await self.client.get('/api/family_tasks/frontend/card.js', headers={
            'If-None-Match': '"obsolete"',
            'If-Modified-Since': 'Tue, 01 Jan 2030 00:00:00 GMT',
        })
        self.assertEqual(response.status, 200)
        self.assert_no_cache(response)
        self.assertEqual(await response.read(), self.path.read_bytes())

    async def test_head_has_same_cache_policy_without_body(self):
        for url in [self.view.url, *self.view.extra_urls]:
            response = await self.client.head(url)
            self.assertEqual(response.status, 200)
            self.assert_no_cache(response)
            self.assertEqual(await response.read(), b"")

    async def test_missing_implementation_is_not_cached(self):
        self.path.unlink()
        for url in self.view.extra_urls:
            response = await self.client.get(url)
            self.assertEqual(response.status, 404)
            self.assert_no_cache(response)

    async def test_unknown_paths_are_not_exposed(self):
        response = await self.client.get('/api/family_tasks/frontend/../store.py')
        self.assertEqual(response.status, 404)
