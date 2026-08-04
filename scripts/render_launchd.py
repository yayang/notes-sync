#!/usr/bin/env python3
"""Render a portable LaunchAgent plist for the current checkout."""

from __future__ import annotations

import argparse
import plistlib
from pathlib import Path
from typing import Any

PROJECT_ROOT_PLACEHOLDER = "{{PROJECT_ROOT}}"
LOG_DIR_PLACEHOLDER = "{{LOG_DIR}}"


def _replace_placeholders(
    value: Any, project_root: str, log_dir: str
) -> Any:
    if isinstance(value, str):
        return (
            value.replace(PROJECT_ROOT_PLACEHOLDER, project_root)
            .replace(LOG_DIR_PLACEHOLDER, log_dir)
        )
    if isinstance(value, list):
        return [_replace_placeholders(item, project_root, log_dir) for item in value]
    if isinstance(value, dict):
        return {
            key: _replace_placeholders(item, project_root, log_dir)
            for key, item in value.items()
        }
    return value


def render_launchd(
    source: Path, output: Path, project_root: Path, log_dir: Path
) -> None:
    """Render a plist and replace path placeholders."""
    with source.open("rb") as stream:
        config = plistlib.load(stream)

    rendered = _replace_placeholders(
        config, str(project_root.resolve()), str(log_dir.expanduser().resolve())
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as stream:
        plistlib.dump(rendered, stream, sort_keys=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--log-dir", type=Path, required=True)
    args = parser.parse_args()
    render_launchd(args.source, args.output, args.project_root, args.log_dir)


if __name__ == "__main__":
    main()
