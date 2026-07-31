# Integrations

[English](INTEGRATIONS.md) | [简体中文](INTEGRATIONS.zh-CN.md)

## Toggl

- Store the [API token](https://engineering.toggl.com/docs/authentication/) in `.env`.
- Notes Sync resolves the [Project list](https://engineering.toggl.com/docs/api/projects/) and [Client list](https://engineering.toggl.com/docs/api/clients/); exact category rules live in [`statistics/mapping.py`](../src/notes_sync/infrastructure/processors/statistics/mapping.py).

## Notion

- [Duplicate the Journal template](https://mysterious-dive-fb9.notion.site/Notes-Sync-Journal-Template-3ae15d9eb4a880c98bcfd7710588856e?source=copy_link).
- Follow the [Integration authorization guide](https://developers.notion.com/guides/get-started/authorization), then store the token and database ID in `.env`.

## Obsidian

### Host

- Scheduled execution and the local `rsync` mirror are designed for macOS. Windows is not verified.

### iOS

- Without Git: store the vault in Obsidian's iCloud directory for simple bidirectional sync.
- With Git: most users should keep the vault local and use paid [Obsidian Sync](https://obsidian.md/help/Getting%2Bstarted/Sync%2Byour%2Bnotes%2Bacross%2Bdevices).
- Advanced Git setup: keep the vault in a local worktree and mirror it to iCloud with `rsync`; do not put the worktree itself in iCloud.
- Steps: Health automation → [Shortcut](../deploy/shortcuts/README.md) → iCloud `health_data.txt` → macOS `STEPS_DATA_FILE`.

### Android

- Vault: prefer Obsidian Sync; Syncthing-Fork is an external mobile-side, local-first option.
- Steps: use an agent to implement and validate your own adapter.
