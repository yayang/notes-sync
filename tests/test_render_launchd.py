import plistlib
from pathlib import Path

from scripts.render_launchd import render_launchd


def test_render_launchd_replaces_project_root(tmp_path: Path):
    source = tmp_path / "source.plist"
    output = tmp_path / "output.plist"
    project_root = tmp_path / "project"
    source.write_bytes(
        plistlib.dumps(
            {
                "WorkingDirectory": "{{PROJECT_ROOT}}",
                "ProgramArguments": ["{{PROJECT_ROOT}}/.venv/bin/python"],
            }
        )
    )

    render_launchd(source, output, project_root)

    rendered = plistlib.loads(output.read_bytes())
    assert rendered["WorkingDirectory"] == str(project_root)
    assert rendered["ProgramArguments"] == [
        f"{project_root}/.venv/bin/python"
    ]
