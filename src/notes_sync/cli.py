import json
import logging
from pathlib import Path

import typer

from notes_sync.config.settings import GlobalSettings
from notes_sync.main import main as core_main
from notes_sync.main import create_diary as core_create_diary

app = typer.Typer(help="Daily Notes Sync Tool")


def load_config(config_path: Path) -> dict:
    """Load configuration from a JSON file."""
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


@app.command()
def run(
    config: Path = typer.Option(
        ...,
        "--config",
        "-c",
        help="Path to the JSON configuration file.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
):
    """
    Run the sync tool with the specified configuration.
    """
    try:
        # 1. Load JSON Config
        config_data = load_config(config)

        # 2. Merge with Env (Pydantic does this by init)
        # However, passing kwargs to GlobalSettings() overrides env vars by default in Pydantic V2
        # or we might need to be careful about precedence.
        # Ideally: Env < Config File

        # In Pydantic BaseSettings, arguments passed to __init__ take precedence over env vars.
        # So we can just unpack config_data.

        settings = GlobalSettings(**config_data)

        # 3. Validation is automatic via Pydantic

        # 4. Run Core Logic
        core_main(settings=settings)

    except Exception as e:
        typing_logger = logging.getLogger("typer")
        typing_logger.error(f"Failed to initialize application: {e}")
        raise typer.Exit(code=1)


@app.command("create-diary")
def create_diary(
    config: Path = typer.Option(
        ...,
        "--config",
        "-c",
        help="Path to the JSON configuration file.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
):
    """Create today's diary in sinks where it is missing."""
    try:
        settings = GlobalSettings(**load_config(config))
        core_create_diary(settings=settings)
    except Exception as e:
        logging.getLogger("typer").error(f"Failed to create diary: {e}")
        raise typer.Exit(code=1)


@app.command()
def version():
    """Show version information."""
    typer.echo("Antigravity Sync Engine v0.1.0")


if __name__ == "__main__":
    app()
