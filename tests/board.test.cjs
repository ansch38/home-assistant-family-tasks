// Execute the actual card with a small DOM double; no browser packages required.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const {join} = require('node:path');
const vm = require('node:vm');

class ShadowRoot {
  constructor() {
    this.error = {textContent: ''};
    this.inputs = [];
    this.sections = {};
    const field = value => ({value, addEventListener() {}});
    this.form = {
      elements: {
        frequency: field('yearly'), title: field('Edited annual task'),
        person: field('Testperson'), time_of_day: field('evening'),
        missed_behavior: field('keep'), year_month: field('2'), year_day: field('29'),
      },
      querySelectorAll() {return [];},
    };
  }
  set innerHTML(html) {
    this.html = html;
    this.inputs = [...html.matchAll(/<input type="checkbox" data-uid="([^"]+)"([^>]*)>/g)]
      .map(([, uid, attributes]) => ({dataset: {uid}, checked: attributes.includes('checked'), disabled: attributes.includes('disabled')}));
  }
  get innerHTML() {return this.html;}
  querySelectorAll(selector) {return selector === 'input[data-uid]' ? this.inputs : [];}
  querySelector(selector) {
    if (selector === '#board-error' || selector === '#message') return this.error;
    if (selector === '#task') return this.form;
    if (['#weekly', '#monthly', '#yearly'].includes(selector)) return this.sections[selector] ||= {};
    return null;
  }
}

function fixture() {
  const elements = new Map();
  // Simulate a tablet whose clock and local day disagree with Home Assistant.
  class TabletDate extends Date {
    constructor(...args) {super(...(args.length ? args : ['2035-01-01T01:00:00Z']));}
  }
  const context = vm.createContext({
    HTMLElement: class {attachShadow() {this.shadowRoot = new ShadowRoot();}},
    customElements: {define: (name, value) => elements.set(name, value)},
    window: {}, Date: TabletDate,
  });
  vm.runInContext(readFileSync(join(__dirname, '../custom_components/family_tasks/family-tasks-card.js'), 'utf8'), context);
  const attributes = {
    today: '2026-11-04', people: [{id: 'p', name: 'Testperson'}],
    tasks: [{id: 't', person_id: 'p', title: 'Old open task', time_of_day: 'anytime'}],
    history: [],
    current_instances: [{id: 'old', task_id: 't', date: '2026-01-01', status: 'open', completed_at: null}],
  };
  const hass = {
    config: {time_zone: 'Europe/Berlin'},
    states: {'sensor.family_tasks_catalog': {attributes}},
    async callService() {},
  };
  const board = new (elements.get('family-tasks-board-card'))();
  board.setConfig({});
  board.hass = hass;
  return {attributes, board, hass, elements};
}

test('board displays old open instances outside the history window', () => {
  const {board} = fixture();
  assert.equal(board.shadowRoot.inputs.length, 1);
  assert.equal(board.shadowRoot.inputs[0].dataset.uid, 'old');
  assert.match(board.shadowRoot.innerHTML, /0 von 1 erledigt/);
});

test('board uses backend day for heading and overdue indication despite tablet clock', () => {
  const {board, attributes, hass} = fixture();
  attributes.current_instances[0].date = '2026-11-04';
  board.hass = hass;
  assert.match(board.shadowRoot.innerHTML, /Mittwoch,? 4\. November 2026/);
  assert.doesNotMatch(board.shadowRoot.innerHTML, /Überfällig seit/);
  attributes.current_instances[0].date = '2026-11-03';
  board.hass = hass;
  assert.match(board.shadowRoot.innerHTML, /Überfällig seit/);
});

test('empty current selection is authoritative even if history contains items', () => {
  const {board, attributes, hass} = fixture();
  attributes.history = attributes.current_instances;
  attributes.current_instances = [];
  board.hass = hass;
  assert.equal(board.shadowRoot.inputs.length, 0);
});

test('overdue completion stays visible, supports undo, and unlocks replacement checkbox', async () => {
  const {board, attributes, hass} = fixture();
  const calls = [];
  hass.callService = async (domain, service, data) => {
    calls.push([domain, service, {...data}]);
    attributes.current_instances[0].status = data.status === 'completed' ? 'done' : 'open';
    attributes.current_instances[0].completed_at = data.status === 'completed' ? '2026-11-04T12:00:00+01:00' : null;
    board.hass = hass;
  };
  const original = board.shadowRoot.inputs[0];
  original.checked = true;
  await original.onchange();
  const replacement = board.shadowRoot.inputs[0];
  assert.notEqual(replacement, original);
  assert.equal(replacement.checked, true);
  assert.equal(replacement.disabled, false);
  assert.match(board.shadowRoot.innerHTML, /1 von 1 erledigt/);
  replacement.checked = false;
  await replacement.onchange();
  assert.equal(board.shadowRoot.inputs[0].checked, false);
  assert.equal(board.shadowRoot.inputs[0].disabled, false);
  assert.deepEqual(calls.map(call => call[2].status), ['completed', 'needs_action']);
  assert.equal(calls[0][0], 'todo');
  assert.equal(calls[0][1], 'update_item');
  assert.equal(calls[0][2].item, 'old');
});

test('backend day change expires completed items without relying on tablet midnight', () => {
  const {board, attributes, hass} = fixture();
  attributes.current_instances[0].status = 'done';
  board.hass = hass;
  assert.equal(board.shadowRoot.inputs[0].checked, true);
  attributes.today = '2026-11-05';
  attributes.current_instances = [];
  board.hass = hass;
  assert.equal(board.shadowRoot.inputs.length, 0);
  assert.match(board.shadowRoot.innerHTML, /Donnerstag,? 5\. November 2026/);
});

test('failed status call restores checkbox and shows error', async () => {
  const {board, hass} = fixture();
  hass.callService = async () => {throw new Error('Test failure');};
  const input = board.shadowRoot.inputs[0];
  input.checked = true;
  await input.onchange();
  assert.equal(input.checked, false);
  assert.equal(input.disabled, false);
  assert.match(board.shadowRoot.error.textContent, /Test failure/);
});

test('older backend is reported explicitly instead of silently truncating tasks', () => {
  const {board, attributes, hass} = fixture();
  delete attributes.current_instances;
  delete attributes.today;
  board.hass = hass;
  assert.match(board.shadowRoot.innerHTML, /Integration aktualisieren/);
});

test('yearly edit submits month and day through the management card', async () => {
  const {elements, hass} = fixture();
  const card = new (elements.get('family-tasks-card'))();
  card.setConfig({});
  card.hass = hass;
  card.editId = 't';
  card.render();
  const calls = [];
  hass.callService = async (...args) => calls.push(args);
  await card.shadowRoot.form.onsubmit({preventDefault() {}, target: card.shadowRoot.form});
  assert.equal(calls.length, 1);
  assert.equal(calls[0][0], 'family_tasks');
  assert.equal(calls[0][1], 'update_task');
  assert.equal(calls[0][2].task_id, 't');
  assert.equal(calls[0][2].month, 2);
  assert.equal(calls[0][2].day, 29);
});
