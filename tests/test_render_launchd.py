import plistlib
from pathlib import Path

from scripts.render_launchd import render_launchd


def test_render_launchd_replaces_path_placeholders(tmp_path: Path):
    source = tmp_path / "source.plist"
    output = tmp_path / "output.plist"
    project_root = tmp_path / "project"
    log_dir = tmp_path / "logs"
    source.write_bytes(
        plistlib.dumps(
            {
                "WorkingDirectory": "{{PROJECT_ROOT}}",
                "ProgramArguments": ["{{PROJECT_ROOT}}/.venv/bin/python"],
                "StandardOutPath": "{{LOG_DIR}}/hourly.log",
            }
        )
    )

    render_launchd(source, output, project_root, log_dir)

    rendered = plistlib.loads(output.read_bytes())
    assert rendered["WorkingDirectory"] == str(project_root)
    assert rendered["ProgramArguments"] == [
        f"{project_root}/.venv/bin/python"
    ]
    assert rendered["StandardOutPath"] == f"{log_dir}/hourly.log"
