<p align="center">
  <img src="images/family-tasks-logo.png" alt="Family Tasks logo" width="220">
</p>

<h1 align="center">Family Tasks for Home Assistant</h1>

<p align="center">
  A family-friendly Home Assistant integration for recurring household tasks.
</p>

---

Family Tasks helps households organize recurring chores for multiple family members. It includes a tablet-friendly family board, task management in Home Assistant, and native To-do and Calendar entities.

## Features

- Assign recurring tasks to individual family members.
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

New tasks default to **Discard**. Tasks created before this setting was introduced retain the previous **Archive** behavior unless you change it.

A kept-open task retains its original due date. Once completed, subsequent occurrences follow its normal recurrence rule. An overdue task completed today can also be unchecked again on the same day.

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

## Updates and data

Install published updates through HACS and restart Home Assistant. After frontend changes, reload the browser or app. Keep the dashboard resource URL set to `/family_tasks/family-tasks-card.js`.

Task definitions, family members, and history are stored locally in Home Assistant's `.storage` directory, separately from the integration's code files. **Back up Home Assistant before upgrading**, and do not delete the stored Family Tasks data when replacing the integration files.

Never commit tokens, passwords, `secrets.yaml`, `.storage`, databases, backups, private keys, or personal household task data to a public repository.

## Development status

Family Tasks is under active development. Until version 1.0, functionality and internal data structures may change. Feedback, bug reports, and suggestions are welcome through GitHub Issues.

## License

Family Tasks is licensed under the [MIT License](LICENSE).
