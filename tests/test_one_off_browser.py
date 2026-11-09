"""Real DOM and cache checks wired to real store/service code via a test HTTP API."""

import asyncio
import subprocess
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

import test_frontend_browser as browser_support
from test_regressions import CLOCK, INTEGRATION, ROOT, SENSOR, TODO, make_hass, real_vol

ENABLED = browser_support.ENABLED
if ENABLED:
    from aiohttp import web
    from playwright.async_api import expect


@unittest.skipUnless(ENABLED and real_vol is not None, "Enable browser tests and install requirements-browser.txt")
class OneOffBrowserTests(unittest.IsolatedAsyncioTestCase):
    load_card = browser_support.FrontendBrowserTests.load_card

    async def asyncSetUp(self):
        clock_patch = patch.object(CLOCK, "now", lambda: datetime(2026, 11, 9, 12, tzinfo=timezone(timedelta(hours=1))))
        clock_patch.start()
        self.addCleanup(clock_patch.stop)
        self.service_hass = make_hass()
        self.callbacks = []
        entry = SimpleNamespace(entry_id="one-off", async_on_unload=self.callbacks.append)
        await INTEGRATION.async_setup_entry(self.service_hass, entry)
        self.store = self.service_hass.data["family_tasks"]["one-off"]
        await self.store.add_person("Testperson")
        self.calls = []
        self.block_add = False
        self.add_started = asyncio.Event()
        self.add_release = asyncio.Event()
        await browser_support.FrontendBrowserTests.asyncSetUp(self)
        self.new_source = (ROOT / 'family-tasks-card.js').read_text(encoding='utf-8')
        self.path.write_text(self.new_source + '\nwindow.familyTasksVersion="one-off";', encoding='utf-8')
        await self.load_card()
        await self.mount()

    def catalog(self):
        return SENSOR.FamilyCatalog(self.store, "one-off").extra_state_attributes

    def add_routes(self, app):
        async def catalog(request):
            return web.json_response(self.catalog())

        async def service(request):
            body = await request.json()
            domain, name, data = body['domain'], body['service'], body['data']
            self.calls.append((domain, name, data))
            if name == 'add_task':
                self.add_started.set()
                if self.block_add:
                    await self.add_release.wait()
            try:
                if domain == 'family_tasks':
                    validated = self.service_hass.schemas[(domain, name)](data)
                    await self.service_hass.handlers[(domain, name)](SimpleNamespace(data=validated))
                elif domain == 'todo' and name == 'update_item':
                    await TODO.FamilyTodo(self.store, "one-off").async_update_todo_item(
                        SimpleNamespace(uid=data['item'], status=data['status'])
                    )
                else:
                    return web.json_response({'error':'Unknown test service'}, status=404)
            except (ValueError, real_vol.Invalid) as error:
                return web.json_response({'error':str(error)}, status=400)
            return web.json_response(self.catalog())

        app.router.add_get('/test/catalog', catalog)
        app.router.add_post('/test/service', service)

    async def mount(self):
        await self.page.evaluate("""async () => {
          const attributes = await (await fetch('/test/catalog')).json();
          const manage = document.createElement('family-tasks-card');
          const board = document.createElement('family-tasks-board-card');
          const hass = {
            states:{'sensor.family_tasks_catalog':{attributes}},
            async callService(domain, service, data) {
              const response = await fetch('/test/service', {
                method:'POST', headers:{'Content-Type':'application/json'},
                body:JSON.stringify({domain,service,data})
              });
              const result = await response.json();
              if (!response.ok) throw new Error(result.error);
              this.states['sensor.family_tasks_catalog'].attributes = result;
              manage.hass=this;board.hass=this;
            }
          };
          manage.setConfig({});board.setConfig({});
          manage.hass=hass;board.hass=hass;
          document.body.append(manage,board);
        }""")

    async def fill_once(self, due='2026-11-09', title='Browser one-off'):
        form = self.page.locator('family-tasks-card #task')
        await form.locator('[name=title]').fill(title)
        await form.locator('[name=person]').select_option('Testperson')
        await form.locator('[name=frequency]').select_option('once')
        self.assertEqual(await form.locator('[name=missed_behavior]').input_value(), 'keep')
        await form.locator('[name=start]').fill(due)
        return form

    async def test_create_complete_undo_move_and_restore_in_real_dom(self):
        form = await self.fill_once()
        await form.locator('#save-task').click()
        manage = self.page.locator('family-tasks-card')
        board = self.page.locator('family-tasks-board-card')
        await expect(manage.locator('.item')).to_have_count(1)
        await expect(board.locator('input[type=checkbox]')).to_have_count(1)
        uid = self.store.data['instances'][0]['id']
        checkbox = board.locator('input[type=checkbox]')
        await checkbox.check()
        await expect(checkbox).to_be_checked()
        await manage.locator('[data-edit]').click()
        self.assertTrue(await manage.locator('[name=start]').evaluate('input => input.readOnly'))
        self.assertTrue(await manage.locator('[name=frequency]').is_disabled())
        await checkbox.uncheck()
        await expect(manage.locator('[name=start]')).to_be_editable()
        await manage.locator('[name=start]').fill('2040-02-29')
        await manage.locator('#save-task').click()
        await expect(board.locator('input[type=checkbox]')).to_have_count(0)
        self.assertEqual(self.store.data['instances'][0]['id'], uid)
        self.assertEqual(self.store.data['instances'][0]['date'], '2040-02-29')
        await manage.locator('[data-edit]').click()
        await manage.locator('[name=start]').fill('2026-11-01')
        await manage.locator('#save-task').click()
        await expect(board.locator('input[type=checkbox]')).to_have_count(1)
        self.assertEqual(self.store.data['instances'][0]['id'], uid)
        await self.store.rollover()
        self.assertEqual(len(self.store.data['instances']), 1)

    async def test_native_date_validation_and_deliberate_behavior_choice(self):
        form = await self.fill_once(due='')
        self.assertFalse(await form.evaluate('form => form.checkValidity()'))
        await form.locator('#save-task').click()
        self.assertEqual(self.calls, [])
        await form.locator('[name=missed_behavior]').select_option('archive')
        await form.locator('[name=frequency]').select_option('daily')
        await form.locator('[name=frequency]').select_option('once')
        self.assertEqual(await form.locator('[name=missed_behavior]').input_value(), 'archive')
        await form.locator('[name=start]').fill('2026-11-01')
        await form.locator('#save-task').click()
        await expect(self.page.locator('family-tasks-card .item')).to_have_count(1)
        self.assertEqual(self.store.data['instances'][0]['status'], 'missed')

    async def test_two_submissions_with_delayed_service_create_one_definition(self):
        form = await self.fill_once()
        self.block_add = True
        await form.evaluate('form => {form.requestSubmit();form.requestSubmit();}')
        await asyncio.wait_for(self.add_started.wait(), timeout=5)
        await expect(form.locator('#save-task')).to_be_disabled()
        self.assertEqual(len(self.calls), 1)
        self.add_release.set()
        await expect(self.page.locator('family-tasks-card .item')).to_have_count(1)
        self.assertEqual(len(self.store.data['tasks']), 1)
        self.assertEqual(len(self.store.data['instances']), 1)

    async def test_stable_cached_loader_picks_up_actual_one_off_card_update(self):
        previous = subprocess.check_output(['git', 'show', 'v0.6.2:custom_components/family_tasks/family-tasks-card.js'], encoding='utf-8')
        self.path.write_text(previous + '\nwindow.familyTasksVersion="previous";', encoding='utf-8')
        await self.page.reload()
        await self.load_card()
        await self.mount()
        await expect(self.page.locator('family-tasks-card option[value=once]')).to_have_count(0)
        self.path.write_text(self.new_source + '\nwindow.familyTasksVersion="updated";', encoding='utf-8')
        await self.page.reload()
        await self.load_card()
        await self.mount()
        await expect(self.page.locator('family-tasks-card option[value=once]')).to_have_count(1)
        resource = await self.page.locator('script[type=module]').get_attribute('src')
        self.assertEqual(resource, '/family_tasks/family-tasks-card.js')
        form = await self.fill_once(due='2040-02-29')
        await form.locator('#save-task').click()
        await expect(self.page.locator('family-tasks-card .item')).to_have_count(1)
        self.assertEqual(self.store.data['tasks'][0]['frequency'], 'once')
