<p align="center">
  <img src="images/family-tasks-logo.png" alt="Family Tasks logo" width="220">
</p>

<h1 align="center">Family Tasks for Home Assistant</h1>

<p align="center">
  A family-friendly Home Assistant integration for one-off and recurring household tasks.
</p>

---

Family Tasks helps households organize one-off and recurring chores for multiple family members. It includes a tablet-friendly family board, task management in Home Assistant, and native To-do and Calendar entities.

## Features

- Assign one-off or recurring tasks to individual family members.
- Give one-off tasks an explicit due date, with no follow-up occurrence.
- Repeat tasks **daily, weekly, monthly, or yearly**.
- Organize tasks by **Morning, Daytime, Evening, or Anytime**.
- Choose what happens to an unfinished task: **Discard, Archive, or Keep open**.
- See overdue tasks on the family board and mark them complete.
- Check off tasks directly from a touch-friendly, person-based tablet dashboard.
- Track open, completed, and missed tasks with Home Assistant entities.
- Store task definitions and history locally in Home Assistant; no Family Tasks cloud service is required.

## Installation

### HACS (recommended)

1. In HACS, add `https://github.com/ansch38/home-assistant-family-tasks` as a **custom repository** of type **Integration**.
2. Install **Family Tasks** and restart Home Assistant.
3. Go to **Settings → Devices & services → Add integration** and select **Family Tasks**. If it is already configured, you do not need to add it again.
4. In **Settings → Dashboards → Resources**, register the following URL as a **JavaScript module**:

   ```text
   /family_tasks/family-tasks-card.js
   ```

   You only need to register the resource once. If your dashboard still shows an older card after updating, reload the browser or Home Assistant app.

### Manual installation

Copy `custom_components/family_tasks/` from this repository to your Home Assistant configuration directory, so the files are located under `/config/custom_components/family_tasks/`. Restart Home Assistant, add the integration, and register the dashboard resource shown above.

## Dashboard cards

### Family tablet board

```yaml
type: custom:family-tasks-board-card
title: Our Family Tasks
catalog_entity: sensor.family_tasks_catalog
todo_entity: todo.family_tasks
columns: 4
```

The board displays today's tasks in columns by family member, grouped by time of day. It includes progress indicators and a touch-friendly design, and highlights overdue tasks. A **Panel** dashboard view is useful for wall-mounted tablets.

The board and native To-do list use the same current occurrences. Overdue tasks
completed today remain visible and can be unchecked for the rest of the day.
The displayed day comes from Home Assistant, so a tablet's time zone or clock
does not change which tasks are shown. Day changes are published on the next
five-minute integration tick, even if no new tasks are due.

If you omit `columns`, the board adjusts its column count to the available width. You can optionally set `min_column_width` (for example, `260`) when using automatic columns.

### Task management

```yaml
type: custom:family-tasks-card
catalog_entity: sensor.family_tasks_catalog
```

Create, edit, and delete task definitions here, including assignee, time of day, recurrence, and unfinished-task behavior.

### Family member management

```yaml
type: custom:family-tasks-people-card
catalog_entity: sensor.family_tasks_catalog
```

Add family members using this card. Renaming and deleting people is not currently supported in the card.

## Task scheduling

| Recurrence | How it works |
| --- | --- |
| Once | Choose a required due date. There is only one occurrence, including after completion, restart, or rescheduling. |
| Daily | A new occurrence is scheduled each day. |
| Weekly | Choose one or more weekdays. |
| Monthly | Choose a day of the month. If the month is shorter, the last day is used. |
| Yearly | Choose a month and day. February 29 falls on February 28 in non-leap years. |

### What happens when a task is not completed?

Each task has its own **When not completed** setting:

| Setting | Behavior | Example |
| --- | --- | --- |
| **Discard** | Remove the unfinished occurrence when it becomes past due. The recurring task definition remains, and its next scheduled occurrence can still be created. | Pack a school bag |
| **Archive** | Mark the unfinished occurrence as `missed` and retain it in the history. | Put out the bins |
| **Keep open** | Keep the original unfinished occurrence visible as overdue until it is completed. Avoid creating another open occurrence for the same task. | Replace a water filter |

New recurring tasks default to **Discard**. New one-off tasks default to **Keep
open**. An explicitly chosen setting is retained. Tasks created before this
setting was introduced retain the previous **Archive** behavior unless you
change it.

A kept-open task retains its original due date. Once completed, subsequent occurrences follow its normal recurrence rule. An overdue task completed today can also be unchecked again on the same day.

### One-off tasks

Choose **Einmalig** in the management card and select **Fällig am** explicitly.
The due date has no time component and uses the Home Assistant calendar day.
Future one-off tasks appear in the management card and calendar; they enter the
board and native To-do list when due. Completing a one-off task never creates a
follow-up. Today's completed occurrence stays visible until the day changes so
it can be unchecked, including if its original due date is older.

Past due dates and long periods of downtime use the selected behavior:

| Setting | One-off behavior |
| --- | --- |
| Keep open | Show the original due date as overdue until completed. |
| Archive | Retain one `missed` occurrence, hidden from current tasks. |
| Discard | Keep the definition without a current occurrence; remove an overdue open occurrence. |

You can reschedule a future or open one-off task. Its occurrence ID remains the
same, and all views update immediately. Moving it into the future hides it from
current tasks until the new due date; moving it into the past applies its missed
behavior immediately. Explicitly rescheduling a discarded task reuses its
reserved occurrence ID. Repeated rollover alone does not recreate discarded
past occurrences.

Completed and archived dates are protected in both the service and the card;
other details can still be edited. Switching between one-off and recurring is
not supported. Definitions are never automatically deleted after completion or
discard. Deleting a definition retains any recorded instances under the existing
history behavior, while removing it from the management card, board, To-do and
calendar. Separately created definitions may intentionally have the same title.

For automations, `family_tasks.add_task` accepts `frequency: once` and requires
`start` as a `YYYY-MM-DD` date. `family_tasks.update_task` accepts `start` to
reschedule a one-off task; omitting it preserves the due date. Omitted
`missed_behavior` on a one-off edit preserves the task's existing choice.

## Home Assistant entities

Family Tasks provides a To-do list, a calendar, a catalog sensor, and counters for task states. Typical entity IDs are:

| Entity | Purpose |
| --- | --- |
| `todo.family_tasks` | Current tasks, including overdue open tasks |
| `calendar.family_tasks` | Scheduled tasks and task history |
| `sensor.family_tasks_catalog` | Family members, task definitions, and instance data used by the cards |
| `sensor.family_tasks_open` | Open-task count |
| `sensor.family_tasks_done` | Completed-task count |
| `sensor.family_tasks_missed` | Missed-task count |

Entity IDs may differ if Home Assistant needs to resolve a naming conflict.

The catalog exposes `today` (the Home Assistant date) and `current_instances`
(all current occurrences, including overdue open tasks and overdue tasks
completed today). The separate `history` attribute remains limited to the last
500 stored occurrences. That limit does not truncate `current_instances`.

## Updates and data

Release notes are available in [CHANGELOG.md](CHANGELOG.md).

Install published updates through HACS and restart Home Assistant. After frontend changes, reload the browser or app. Keep the dashboard resource URL set to `/family_tasks/family-tasks-card.js`.

The stable resource URL now serves a small loader. On each full dashboard reload,
it checks the current card content through a non-cached API endpoint and imports
the implementation using an automatically calculated content hash. You do not
need to maintain version query strings in dashboard resources. The API endpoints
serve bundled JavaScript and its hash only; household data is not exposed there.

For the first upgrade from the old directly served card, a browser or service
worker may still have that previous card cached. Reload again after the first
reload has completed; if it persists, clear that client's Home Assistant frontend
cache once. Server headers cannot invalidate a response already served without
contacting the server. Subsequent card updates use the stable loader. An open
dashboard tab still needs a full page reload to run updated JavaScript.

Manual installations must include the new `frontend.py` file alongside the
updated `__init__.py`. Restart Home Assistant after copying them so the HTTP
routes are replaced. Reverse proxies must not override the API responses'
`Cache-Control: no-store, max-age=0` policy.

When installing this board update, update the integration and reload the browser
together. The board requires the catalog's `today` and `current_instances`
attributes and shows an update notice if they are missing. The storage format
is unchanged; no data migration is needed for these attributes.

Task definitions, family members, and history are stored locally in Home Assistant's `.storage` directory, separately from the integration's code files. **Back up Home Assistant before upgrading**, and do not delete the stored Family Tasks data when replacing the integration files.

One-off support is additive: it uses `frequency: once`, the existing `start`
date, and an optional `once_instance_id` on one-off definitions to reserve a
stable identity even before the first occurrence. The storage key and version
are unchanged; existing people, definitions, instances and IDs are not migrated.
The catalog's `date_locked` flag is derived from recorded history, not stored as
another task status. Older versions such as 0.6.2 do not understand one-off
definitions. Downgrading with one-off data is unsupported; use a compatible
version or restore a backup from before creating one-off tasks.

The Home Assistant function-test checklist is in
[docs/testing-one-off-tasks.md](docs/testing-one-off-tasks.md).

Never commit tokens, passwords, `secrets.yaml`, `.storage`, databases, backups, private keys, or personal household task data to a public repository.

## Development status

### Regression tests

Run the Python regression suite from the repository root:

```shell
python -B -m unittest discover -s tests -v
```

The core tests require only Python. To also validate the registered service
schemas with real voluptuous and exercise the frontend with real aiohttp
requests, install the test dependencies before running the same command:

```shell
python -m pip install -r tests/requirements.txt
```

Run the frontend tests with Node.js (LTS) using its built-in test runner:

```shell
node --test tests/board.test.cjs
```

Optional browser tests execute the loader and real card in a browser, with a
test service worker modeling HA's API/network and file-cache rules. They verify
updates with a cached loader and the one-time transition from a cached old card.
For example, using the already installed Microsoft Edge from PowerShell:

```powershell
python -m pip install -r tests/requirements-browser.txt
$env:FAMILY_TASKS_BROWSER_TESTS = "1"
$env:FAMILY_TASKS_BROWSER_CHANNEL = "msedge"
python -B -m unittest discover -s tests -v
```

Without `FAMILY_TASKS_BROWSER_CHANNEL`, Playwright uses its Chromium installation
(install it separately with `python -m playwright install chromium`). Browser
tests use a fresh test profile and run without a visible window.

The tests use synthetic household data, a controlled clock, and in-memory storage.
They cover recurrence boundaries, unfinished-task behavior, completion and undo,
legacy defaults, persistence without a current occurrence, service rebinding
after an integration reload, current-task selection beyond the history limit,
day changes without new instances, and the one-off lifecycle including long
downtime, stable IDs, rescheduling, protected dates, and service validation.
Frontend tests execute the card with DOM
test doubles, including completion/undo, a differing tablet clock, and annual
edit submission. HTTP tests check cache headers, conditional requests, content
hash changes, HEAD requests, and missing files. Home Assistant APIs are replaced
with test doubles; these tests do not validate Home Assistant's actual storage
or HTTP view registration. Browser tests use a simulated worker, not HA's full
frontend. A running Home Assistant smoke test is still needed to verify those
boundaries. No real `.storage` files are read or written.

The one-off browser tests connect the real management card and board to the real
store and registered service schemas through a test-only HTTP transport. They
also verify double-submit prevention and updating the actual 0.6.2 card to the
one-off implementation through the unchanged resource URL.

Family Tasks is under active development. Until version 1.0, functionality and internal data structures may change. Feedback, bug reports, and suggestions are welcome through GitHub Issues.

## License

Family Tasks is licensed under the [MIT License](LICENSE).
