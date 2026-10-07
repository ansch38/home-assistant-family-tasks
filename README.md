<p align="center">
  <img src="images/family-tasks-logo.png" alt="Family Tasks logo" width="220">
</p>

<h1 align="center">Family Tasks for Home Assistant</h1>

<p align="center">
  A family-friendly Home Assistant integration for recurring household tasks.
</p>


Family Tasks is a custom Home Assistant integration for recurring household tasks for multiple family members, with a tablet-friendly family board.

## Features

- Multiple family members
- Daily, weekly and monthly recurring tasks
- Morning, Daytime, Evening and Anytime categories
- Person-based tablet dashboard
- Complete tasks directly from the dashboard
- Home Assistant To-do and Calendar entities
- Missed-task archive and completion history
- Local Home Assistant storage; no Family Tasks cloud service

## Installation with HACS

1. Add `https://github.com/ansch38/home-assistant-family-tasks` as a HACS custom repository of type **Integration**.
2. Install Family Tasks and restart Home Assistant.
3. Go to **Settings → Devices & services → Add integration** and add **Family Tasks**. If it was already configured, do not add it again.
4. In **Settings → Dashboards → Resources**, add this resource once as a JavaScript module:

   `/family_tasks/family-tasks-card.js`

   **Since v0.5.0, keep this URL unchanged for future updates. Do not append `?v=...`.** The integration serves the dashboard card directly from this stable resource URL.

## Dashboard cards

### Task management

```yaml
type: custom:family-tasks-card
catalog_entity: sensor.family_tasks_catalog
```

### Family member management

```yaml
type: custom:family-tasks-people-card
catalog_entity: sensor.family_tasks_catalog
```

### Tablet family board

```yaml
type: custom:family-tasks-board-card
title: Our Family Tasks
catalog_entity: sensor.family_tasks_catalog
todo_entity: todo.family_tasks
columns: 4
```

If `columns` is omitted, the board adapts to the available width. A Home Assistant Panel (single card) view works well for wall-mounted tablets.

## Entities

Typical entity IDs are `todo.family_tasks`, `calendar.family_tasks`, `sensor.family_tasks_catalog`, `sensor.family_tasks_open`, `sensor.family_tasks_done`, and `sensor.family_tasks_missed`. IDs can differ if Home Assistant has to resolve a naming conflict.

## Recurrence and missed tasks

Daily, selected-weekday weekly, and day-of-month monthly recurrences are supported. For a monthly task whose selected day does not exist, the last day of that month is used. When an open occurrence passes its due date, it is archived as `missed`; a new occurrence is created according to the recurrence rule.

## Data and privacy

Family members, task definitions and history are stored locally in Home Assistant storage. They are not stored in this repository or sent to a Family Tasks cloud service. Create a Home Assistant backup before upgrades. Never commit Home Assistant tokens, passwords, `secrets.yaml`, `.storage`, databases, backups, private keys or personal task data.

## Updating

Install new releases through HACS and restart Home Assistant. Starting with v0.5.0, the dashboard resource URL remains `/family_tasks/family-tasks-card.js`; manual cache-buster changes are no longer needed.

## Development status

Family Tasks is under active development. Until version 1.0, functionality, configuration and internal data structures may change.

## License

Family Tasks is released under the MIT License. See `LICENSE` for the full license text.
