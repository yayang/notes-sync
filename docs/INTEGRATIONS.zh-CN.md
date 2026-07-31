# 接入

[English](INTEGRATIONS.md) | [简体中文](INTEGRATIONS.zh-CN.md)

## Toggl

- 将 [API token](https://engineering.toggl.com/docs/authentication/) 保存到 `.env`。
- Notes Sync 会读取 [Project 列表](https://engineering.toggl.com/docs/api/projects/) 和 [Client 列表](https://engineering.toggl.com/docs/api/clients/)；精确分类规则见 [`statistics/mapping.py`](../src/notes_sync/infrastructure/processors/statistics/mapping.py)。

## Notion

- [复制 Journal 模板](https://mysterious-dive-fb9.notion.site/Notes-Sync-Journal-Template-3ae15d9eb4a880c98bcfd7710588856e?source=copy_link)。
- 按照 [Integration 授权说明](https://developers.notion.com/guides/get-started/authorization) 完成授权，再将 token 和 database ID 保存到 `.env`。

## Obsidian

### 主机

- 定时执行与本地 `rsync` 镜像面向 macOS；Windows 尚未验证。

### iOS

- 不使用 Git：将 Vault 放入 Obsidian 的 iCloud 目录，简单实现双向同步。
- 使用 Git：普通用户建议将 Vault 保存在本地目录，并购买 [Obsidian Sync](https://obsidian.md/help/Getting%2Bstarted/Sync%2Byour%2Bnotes%2Bacross%2Bdevices)。
- Git 进阶方案：本地 worktree 保存 Vault，通过 `rsync` 镜像到 iCloud；不建议把 worktree 本身放入 iCloud。
- 步数链路：健康自动化 → [Shortcut](../deploy/shortcuts/README.md) → iCloud `health_data.txt` → macOS `STEPS_DATA_FILE`。

### Android

- Vault：优先使用 Obsidian Sync；Syncthing-Fork 是手机端外部本地优先方案。
- 步数：建议自行使用 agent 实现并验证。
