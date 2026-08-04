# Notes Sync

[English](README.md) | [简体中文](README.zh-CN.md)

Synchronize Toggl Track time entries to Notion and Obsidian.

Notes Sync uses short-lived commands instead of a resident background service.
On macOS, two independent LaunchAgents handle hourly synchronization and daily
diary creation.

## Features

- Synchronize Toggl Track time entries to Notion and Obsidian.
- Create missing daily diary entries with a separate command.
- Run hourly synchronization at minute `0`.
- Configure the daily diary schedule in its plist template.
- Keep secrets, machine paths, logs, and personal data outside Git.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Toggl Track API token
- Notion integration token and database ID
- Obsidian vault
- macOS for scheduled execution

## Setup

Run these commands from the repository root.

1. Install dependencies.

   ```bash
   make install
   ```

   Verify: `.venv/bin/python --version` reports Python 3.12 or newer.

2. Create local configuration.

   ```bash
   cp .env.example .env
   cp params/examples/default.json params/default.json
   ```

   Fill in `.env`. Both `.env` and `params/default.json` are ignored by Git.

3. Run one synchronization.

   ```bash
   make run
   ```

   Verify: `~/Library/Logs/notes-sync/notes_sync.log` contains a completed sync cycle.

4. On macOS, install and restart both schedules.

   ```bash
   make restart-schedules
   ```

   This renders the portable plist templates with the current project path,
   deploys them to `~/Library/LaunchAgents`, and reloads both schedules.

## Scheduling

- `com.notes-sync.hourly`: runs synchronization at the start of every hour.
- `com.notes-sync.create-diary`: creates the daily diary at its configured
  `Hour` and `Minute`.

Application logs are written to `~/Library/Logs/notes-sync/notes_sync.log`; launchd output is written to `hourly.log` and `create-diary.log` in the same directory. `80_Runtime/20_Logs/notes-sync/` is a workspace symlink for convenient access. macOS may coalesce a missed calendar-based run after the computer wakes.

## Development

```bash
make check
make audit
```

`make check` runs mypy and pytest. `make audit` checks installed dependencies
against known vulnerability advisories.

## Configuration

- Secrets and local paths: `.env`
- Runtime behavior: `params/default.json`
- Daily diary time: `deploy/macos/com.notes-sync.create-diary.plist`
- Hourly sync minute: `deploy/macos/com.notes-sync.hourly.plist`

Never commit `.env`, `params/default.json`, logs, caches, or personal migration
data.

The example configuration and reference data are placeholders. Review them
before connecting the project to your own Notion workspace or Obsidian vault.

## Documentation

- [Manual](docs/manual.md)
- [Integrations](docs/INTEGRATIONS.md)
- [Product requirements](docs/PRD.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Security policy](SECURITY.md)

## License

No open-source license is currently granted. Public visibility does not grant
permission to copy, modify, or redistribute this project.
