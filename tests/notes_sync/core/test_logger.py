import io
import logging

from notes_sync.config.settings import LogConfig
from notes_sync.core.logger import setup_logging


class _FakeTty(io.StringIO):
    def isatty(self) -> bool:
        return True


class _FakePipe(io.StringIO):
    def isatty(self) -> bool:
        return False


def test_setup_logging_adds_console_handler_for_tty(tmp_path, monkeypatch):
    """TTY sessions should log to both file and console."""
    monkeypatch.setattr("sys.stdout", _FakeTty())
    config = LogConfig(file_path=str(tmp_path / "tty.log"))

    setup_logging(config)

    handlers = logging.getLogger().handlers
    assert any(isinstance(handler, logging.StreamHandler) for handler in handlers)
    assert any(
        handler.__class__.__name__ == "RotatingFileHandler" for handler in handlers
    )


def test_setup_logging_skips_console_handler_for_non_tty(tmp_path, monkeypatch):
    """Non-interactive sessions should avoid console/file double writes."""
    monkeypatch.setattr("sys.stdout", _FakePipe())
    config = LogConfig(file_path=str(tmp_path / "notes_sync.log"))

    setup_logging(config)

    handlers = logging.getLogger().handlers
    assert len(handlers) == 1
    assert handlers[0].__class__.__name__ == "RotatingFileHandler"
