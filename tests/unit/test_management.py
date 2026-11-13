from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import text

from astronaut_health_monitor.core.configuration import get_application_settings
from astronaut_health_monitor.core.database import create_database_engine
from astronaut_health_monitor.core.field_encryption import generate_encryption_key
from astronaut_health_monitor.management import create_user_from_command_line


@pytest.fixture
def isolated_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    database = tmp_path / "cli.db"
    monkeypatch.setenv("ASTRONAUT_HEALTH_MONITOR_DATABASE_URL", f"sqlite:///{database}")
    monkeypatch.setenv("ASTRONAUT_HEALTH_MONITOR_ENCRYPTION_KEY", generate_encryption_key())
    get_application_settings.cache_clear()
    yield database
    get_application_settings.cache_clear()


def test_command_line_creates_a_user_and_audits_it(isolated_settings: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = create_user_from_command_line(
        ["create-user", "--username", "control.lead", "--role", "mission_control"], password="A-long-test-passphrase1"
    )
    assert code == 0
    assert "Created mission_control account 'control.lead'" in capsys.readouterr().out
    engine = create_database_engine(f"sqlite:///{isolated_settings}")
    with engine.connect() as connection:
        assert connection.execute(text("SELECT role FROM users")).scalar_one() == "mission_control"
        assert connection.execute(text("SELECT action FROM audit_events")).scalar_one() == "user.created"


def test_command_line_reports_bad_details_without_crashing(
    isolated_settings: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = create_user_from_command_line(
        ["create-user", "--username", "ada", "--role", "astronaut"], password="A-long-test-passphrase1"
    )
    assert code == 1
    assert "linked to an existing astronaut" in capsys.readouterr().err
    assert (
        create_user_from_command_line(["create-user", "--username", "doc", "--role", "clinician"], password="short")
        == 1
    )
