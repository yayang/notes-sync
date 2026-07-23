# Antigravity Sync Engine Manual

> Synchronize Toggl time records to Notion and Obsidian.

## 1. 🚀 Quick Start

The project uses `Makefile` as the unified interface.

### Standard Commands

```bash
# 1. Install Dependencies
make install

# 2. Run Sync (One-off)
# Requires a configuration file (defaults to params/default.json)
make run

# Or specify a custom config
make run config=params/custom.json
```

### Scheduling

Hourly sync and daily diary creation run as independent schedules.

```bash
make restart-schedules  # Deploy, reload, and run both schedules
```

Edit `deploy/macos/com.notes-sync.create-diary.plist` to change the daily
`Hour` and `Minute`, then run `make restart-schedules`. Hourly sync uses only
`Minute = 0`, so it runs at the start of every hour.

---

## 2. ⚙️ Configuration

The configuration is split into **Secrets** (Environment) and **Logic** (JSON).

### 2.1 Secrets (.env)

Create a `.env` file for sensitive credentials:

```bash
cp .env.example .env
```

### 2.2 Logic Parameters (JSON)

Create JSON files in `params/` to control runtime behavior.

### 2.3 参数优先级

1. json
2. .env
3. settings.py 默认值

**1. Copy Examples**

Copy the examples to create your active configuration files:

```bash
cp params/examples/default.json params/default.json
```

**2. Customize**

**One-off Sync (`params/default.json`)**:

## 3. 📂 Project Structure

- `src/`: Source code
- `params/`: Configuration files
- `docs/`: Documentation (PRD, Architecture)
- `output/`: Runtime logs

# Official Free Plan Limit

https://developers.notion.com/reference/request-limits
NOTION_PAYLOAD_LIMIT = 500000
NOTION_URL_LIMIT = 2000

https://community.toggl.com/t/api-rate-limit-reset/2310
TOGGL_RATE_LIMIT_PER_HOUR = 30
