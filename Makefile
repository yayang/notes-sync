.PHONY: install run create-diary restart-schedules check audit clean help build-shortcuts prepare-logs

PYTHON := ./.venv/bin/python
UV := uv
SHORTCUTS_OUT := output/shortcuts
LOG_DIR ?= $(HOME)/Library/Logs/notes-sync
LOG_LINK ?= $(HOME)/Developer/10_Workspace/80_Runtime/20_Logs/notes-sync
LOG_FILE := $(LOG_DIR)/notes_sync.log
PROJECT_ROOT := $(abspath .)
LAUNCH_AGENTS_DIR := $(HOME)/Library/LaunchAgents
LAUNCHD_LABELS := com.notes-sync.hourly com.notes-sync.create-diary

##@ General
help: ## Show this help message
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^##@/ {printf "\n%s:\n", substr($$0, 5)} /^[a-zA-Z_-]+:.*?##/ {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

##@ Setup
install: ## Install dependencies using uv
	$(UV) sync

##@ Tasks
prepare-logs:
	@mkdir -p "$(LOG_DIR)" "$(dir $(LOG_LINK))"
	@if [ -e "$(LOG_LINK)" ] && [ ! -L "$(LOG_LINK)" ]; then \
		echo "Log entry exists and is not a symlink: $(LOG_LINK)"; \
		exit 1; \
	fi
	@ln -sfn "$(LOG_DIR)" "$(LOG_LINK)"

run: prepare-logs ## Run the sync tool (usage: make run [config=params/default.json])
	@NOTES_SYNC_LOG_DIR="$(LOG_DIR)" PYTHONPATH=src $(PYTHON) -m notes_sync.cli run --config $(or $(config),params/default.json)

create-diary: prepare-logs ## Create today's missing diary entries
	@NOTES_SYNC_LOG_DIR="$(LOG_DIR)" PYTHONPATH=src $(PYTHON) -m notes_sync.cli create-diary --config $(or $(config),params/default.json)

##@ Scheduling
restart-schedules: prepare-logs ## Deploy, reload, and immediately run both schedules
	@mkdir -p "$(LAUNCH_AGENTS_DIR)"
	@set -e; for label in $(LAUNCHD_LABELS); do \
		destination="$(LAUNCH_AGENTS_DIR)/$$label.plist"; \
		temporary="$$destination.tmp"; \
		$(PYTHON) scripts/render_launchd.py \
			--project-root "$(PROJECT_ROOT)" \
			--log-dir "$(LOG_DIR)" \
			--output "$$temporary" \
			"$(PROJECT_ROOT)/deploy/macos/$$label.plist"; \
		mv -f "$$temporary" "$$destination"; \
	done
	@set -e; uid=$$(id -u); \
	for label in $(LAUNCHD_LABELS); do \
		plist="$(LAUNCH_AGENTS_DIR)/$$label.plist"; \
		launchctl bootout "gui/$$uid/$$label" 2>/dev/null || true; \
		launchctl bootstrap "gui/$$uid" "$$plist"; \
	done
	@echo "Schedules restarted. Logs: $(LOG_FILE)"

##@ Development
check: ## Run type checking and tests
	$(PYTHON) -m mypy src
	$(PYTHON) -m pytest tests

##@ Security
audit: ## Audit installed dependencies for known vulnerabilities
	$(UV) run pip-audit --local --progress-spinner off

##@ Utilities
build-shortcuts: ## Build signed shortcut files into output/shortcuts
	@mkdir -p $(SHORTCUTS_OUT)
	shortcuts sign --mode anyone \
		--input deploy/shortcuts/notes-sync-append-steps.plist \
		--output $(SHORTCUTS_OUT)/notes-sync-append-steps.shortcut

clean: ## Clean up cache and temporary files
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf __pycache__
	find . -type d -name "__pycache__" -delete
