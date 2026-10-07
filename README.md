# Family Tasks for Home Assistant

Family Tasks is a custom Home Assistant integration for managing recurring household tasks for multiple family members.

It is designed especially for family dashboards and wall-mounted tablets.

## Features

- Multiple family members
- Daily, weekly, and monthly recurring tasks
- Assign tasks to individual family members
- Time-of-day categories:
  - 🌅 Morning
  - ☀️ Daytime
  - 🌙 Evening
  - Anytime
- Mark tasks as completed directly from the dashboard
- Automatically create recurring task instances
- Archive missed tasks
- Preserve task completion history
- Home Assistant To-do integration
- Home Assistant Calendar integration
- Tablet-friendly family dashboard
- Separate task and family member management cards
- Local storage
- No external cloud service required

## Dashboard

Family Tasks provides a tablet-friendly dashboard card where each family member is displayed in a separate column.

Within each person's column, tasks are grouped by time of day:

- 🌅 Morning
- ☀️ Daytime
- 🌙 Evening
- Anytime

Tasks can be marked as completed directly from the dashboard.

## Installation

### HACS

1. Open HACS in Home Assistant.
2. Open **Custom repositories**.
3. Add the following repository:

   `https://github.com/ansch38/home-assistant-family-tasks`

4. Select **Integration** as the repository type.
5. Install **Family Tasks**.
6. Restart Home Assistant.
7. Go to **Settings → Devices & services → Add integration**.
8. Search for **Family Tasks** and complete the setup.

> If Family Tasks was already configured before installing it through HACS,
> you do not need to add the integration again.

## Entities

Family Tasks creates several Home Assistant entities.

Typical entity IDs are:

- `todo.family_tasks`
- `calendar.family_tasks`
- `sensor.family_tasks_catalog`
- `sensor.family_tasks_open`
- `sensor.family_tasks_done`
- `sensor.family_tasks_missed`

Entity IDs may differ if entities with the same names already exist in your Home Assistant installation.

## Dashboard Cards

Family Tasks currently provides three custom dashboard cards.

### Task Management

The task management card is used to create and edit recurring tasks.

```yaml
type: custom:family-tasks-card
catalog_entity: sensor.family_tasks_catalog
```

### Family Member Management

Family member management is kept separate because family members usually change much less frequently than tasks.

```yaml
type: custom:family-tasks-people-card
catalog_entity: sensor.family_tasks_catalog
```

### Tablet Family Board

The family board is designed for wall-mounted tablets and larger screens.

Each family member is displayed in a separate column.

```yaml
type: custom:family-tasks-board-card
title: Our Family Tasks
catalog_entity: sensor.family_tasks_catalog
todo_entity: todo.family_tasks
columns: 4
```

Change `columns` to match the number of family members you want to display.

If `columns` is omitted, the card automatically adapts to the available screen width.

For a wall-mounted tablet, a Home Assistant **Panel (single card)** dashboard view is recommended.

## Recurring Tasks

Family Tasks supports several recurrence types.

### Daily

The task is created every day.

Example:

`Empty the dishwasher`

### Weekly

Tasks can be assigned to selected weekdays.

Example:

`Take out the trash — Monday and Thursday`

### Monthly

Tasks can be assigned to a specific day of the month.

Example:

`Change water filter — 15th of every month`

If the selected day does not exist in a particular month, the task is scheduled for the last day of that month.

## Time of Day

Tasks can optionally be assigned to a time-of-day category:

- Morning
- Daytime
- Evening
- Anytime

These categories are currently used for organizing tasks on the dashboard.

They are not yet tied to specific clock times.

Future versions may add optional reminders and configurable time ranges.

## Missed Tasks

When an open task passes its due date without being completed, it is archived as `missed`.

A new task instance is then created according to the recurrence rule.

This allows Family Tasks to preserve the history of previous task occurrences instead of keeping one task permanently overdue.

## Task History

Family Tasks keeps track of task instances and their status.

Possible states include:

- Open
- Completed
- Missed

This makes it possible to retain historical information even when recurring tasks create new instances.

## Data Storage

Family Tasks stores its data locally using Home Assistant's storage system.

Family members, task definitions and task history are not stored in this GitHub repository and are not sent to an external Family Tasks cloud service.

Updating the integration therefore should not remove existing Family Tasks data.

Nevertheless, creating a Home Assistant backup before upgrading is strongly recommended.

## Updating

When installed through HACS, new Family Tasks releases can be installed directly through HACS.

After updating the integration, restart Home Assistant.

## Development Status

Family Tasks is currently under active development.

The project originally started as a custom integration for a family Home Assistant dashboard and is gradually being developed into a reusable Home Assistant integration.

Until version 1.0, functionality, configuration and internal data structures may still change.

## Planned Features

Possible future improvements include:

- Improved HACS frontend integration
- Automatic frontend resource handling
- Easier task editing
- Family member editing and deletion
- Notifications and reminders
- Configurable time ranges for Morning, Daytime and Evening
- Task rotation between family members
- Vacation / pause mode
- Statistics
- Improved task history
- More dashboard customization options

## Privacy

Family Tasks runs locally inside Home Assistant.

No external Family Tasks cloud service is required.

Do not store sensitive Home Assistant data in this repository, including:

- Home Assistant access tokens
- Passwords
- `secrets.yaml`
- `.storage` files
- Home Assistant databases
- Backups
- Private keys
- Personal family task data

## Contributing

Issues, bug reports and suggestions are welcome.

Pull requests can be used to propose improvements or fixes.

## License

Family Tasks is released under the **MIT License**.

Copyright (c) 2026 ansch38

See the `LICENSE` file for the full license text.