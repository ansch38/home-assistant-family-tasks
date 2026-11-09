# Changelog

## Unreleased (planned 0.7.0)

- Add one-off tasks with an explicit calendar due date, assignee and time-of-day
  group. They default to keep open and never create a recurring follow-up.
- Support keep, archive and discard for past dates and long downtime, without
  applying the recurring 366-day backfill limit to a single due date.
- Reschedule future/open one-off tasks immediately with stable occurrence and
  calendar IDs. Completed and archived due dates are protected. Switching
  between one-off and recurring tasks is rejected.
- Add a required due-date field, date-lock notice and protection against duplicate
  submissions to the management card. Explicit missed-behavior choices survive
  frequency selection and edits.
- Keep the existing storage version and all existing recurring-task behavior.
  One-off definitions add only the new frequency and an optional reserved
  occurrence ID. Versions before one-off support cannot safely edit these data;
  downgrades require a compatible version or a pre-feature backup.
- Preserve the stable dashboard resource URL and automatic content-hash loader.
  Browser tests verify updating the actual 0.6.2 card to the new one-off card.
- Home Assistant function testing is pending. Merge and release are gated on
  explicit confirmation of the checklist in `docs/testing-one-off-tasks.md`.

## 0.6.2 — 2026-11-09

Task definitions are saved reliably even when nothing is due today. The family
board and native To-do list now share the same current tasks, and yearly tasks
can be edited with their month intact.

### Fixes

- Persist new task definitions with a future start or no occurrence due today.
- Rebind services to the current store after an integration reload and register
  frontend routes only once per Home Assistant runtime.
- Accept and validate the month when editing yearly tasks.
- Keep overdue tasks completed today visible in the board so completion can be
  undone for the rest of the day.
- Show all current tasks independently of the catalog's 500-item history limit.
- Use Home Assistant's date in the board. Publish day changes on the next
  five-minute tick even when no new instances are created.
- Unlock a checkbox replaced by a catalog update during a pending service call.
- Serve the stable resource URL through a loader that checks the current card
  hash over API endpoints and imports the implementation automatically. Explicit
  no-store headers prevent HTTP cache reuse on those responses.

### Updating

- Update the integration and restart Home Assistant, then fully reload the
  dashboard or app. Existing task data and the storage format are unchanged.
- Keep the dashboard resource URL `/family_tasks/family-tasks-card.js`; remove
  any temporary version query string. Future content versions are automatic.
- During the first upgrade from the old directly served card, an existing
  browser/service-worker cache can require another reload or a one-time frontend
  cache reset before the loader takes over. An already open dashboard requires
  a full reload to run updated JavaScript.
- For manual installations, copy the complete integration folder, including the
  new `frontend.py`. Reverse proxies must respect the API responses' no-store
  policy.

### Validation and limits

- 33 Python, HTTP, and opt-in Edge browser tests and 8 card tests pass.
- Manual Home Assistant checks confirmed restart persistence, service behavior
  after reload, yearly editing, and completion/undo with the stable resource URL.
- Browser tests simulate the relevant service-worker rules; automatic refresh
  after the next real card update remains to be confirmed in the user's Home
  Assistant installation.
