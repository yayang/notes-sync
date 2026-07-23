#!/usr/bin/env python3
"""Render a portable LaunchAgent plist for the current checkout."""

from __future__ import annotations

import argparse
import plistlib
from pathlib import Path
from typing import Any

PROJECT_ROOT_PLACEHOLDER = "{{PROJECT_ROOT}}"


def _replace_project_root(value: Any, project_root: str) -> Any:
    if isinstance(value, str):
        return value.replace(PROJECT_ROOT_PLACEHOLDER, project_root)
    if isinstance(value, list):
        return [_replace_project_root(item, project_root) for item in value]
    if isinstance(value, dict):
        return {
            key: _replace_project_root(item, project_root)
            for key, item in value.items()
        }
    return value


def render_launchd(source: Path, output: Path, project_root: Path) -> None:
    """Render a plist and replace project-root placeholders."""
    with source.open("rb") as stream:
        config = plistlib.load(stream)

    rendered = _replace_project_root(config, str(project_root.resolve()))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as stream:
        plistlib.dump(rendered, stream, sort_keys=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, required=True)
    args = parser.parse_args()
    render_launchd(args.source, args.output, args.project_root)


if __name__ == "__main__":
    main()
