# Notes Sync

[English](README.md) | [简体中文](README.zh-CN.md)

将 Toggl Track 时间记录同步到 Notion 和 Obsidian。

Notes Sync 使用短时命令，而非常驻后台服务。在 macOS 上，两个独立的
LaunchAgent 分别负责每小时同步和每日日记创建。

## 功能

- 将 Toggl Track 时间记录同步到 Notion 和 Obsidian。
- 通过独立命令创建缺失的每日日记。
- 在每小时的第 `0` 分钟运行同步。
- 在 plist 模板中配置每日日记的创建时间。
- 将密钥、本机路径、日志和个人数据排除在 Git 之外。

## 前置条件

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Toggl Track API token
- Notion integration token 和 database ID
- Obsidian vault
- 使用定时任务时需要 macOS

## 安装与使用

在仓库根目录执行以下命令。

1. 安装依赖。

    ```bash
    make install
    ```

    验证：`.venv/bin/python --version` 显示 Python 3.12 或更高版本。

2. 创建本地配置。

    ```bash
    cp .env.example .env
    cp params/examples/default.json params/default.json
    ```

    填写 `.env`。Git 会忽略 `.env` 和 `params/default.json`。

3. 执行一次同步。

    ```bash
    make run
    ```

    验证：`output/notes_sync.log` 包含已完成的同步记录。

4. 在 macOS 上安装并重启两个定时任务。

    ```bash
    make restart-schedules
    ```

    此命令使用当前项目路径渲染可移植的 plist 模板，将其部署到
    `~/Library/LaunchAgents`，然后重新加载两个定时任务。

## 定时任务

- `com.notes-sync.hourly`：每小时整点执行同步。
- `com.notes-sync.create-diary`：在配置的 `Hour` 和 `Minute` 创建每日日记。

两个任务都将日志写入 `output/notes_sync.log`。电脑唤醒后，macOS 可能合并补跑
错过的 calendar-based 任务。

## 开发

```bash
make check
make audit
```

`make check` 运行 mypy 和 pytest。`make audit` 检查已安装依赖的已知漏洞。

## 配置

- 密钥和本机路径：`.env`
- 运行行为：`params/default.json`
- 每日日记时间：`deploy/macos/com.notes-sync.create-diary.plist`
- 每小时同步分钟：`deploy/macos/com.notes-sync.hourly.plist`

不要提交 `.env`、`params/default.json`、日志、缓存或个人迁移数据。

示例配置和参考数据均为占位内容。连接到自己的 Notion workspace 或 Obsidian
vault 前，请先检查并调整。

## 文档

- [使用手册](docs/manual.md)
- [产品需求](docs/PRD.md)
- [架构](docs/ARCHITECTURE.md)
- [安全策略](SECURITY.md)

## 许可证

本项目目前未授予开源许可证。公开可见不代表允许复制、修改或再分发。
