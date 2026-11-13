"""Command line tool to create the first accounts.

    python -m astronaut_health_monitor.management create-user --username control.lead --role mission_control

The password is asked for interactively so it never appears in the shell history.
"""

import argparse
import getpass
import sys
from collections.abc import Sequence
from pathlib import Path

from astronaut_health_monitor.core.configuration import get_application_settings
from astronaut_health_monitor.core.database import create_all_tables, create_database_engine, create_session_factory
from astronaut_health_monitor.core.field_encryption import (
    FieldEncryptor,
    configure_field_encryption,
    load_or_create_encryption_key,
)
from astronaut_health_monitor.domain.enumerations import AuditOutcome, UserRole
from astronaut_health_monitor.domain.exceptions import AstronautHealthMonitorError
from astronaut_health_monitor.repositories.astronaut_repository import AstronautRepository
from astronaut_health_monitor.repositories.audit_repository import AuditRepository
from astronaut_health_monitor.repositories.user_repository import UserRepository
from astronaut_health_monitor.services.audit_service import AuditService
from astronaut_health_monitor.services.authentication_service import AuthenticationService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="astronaut_health_monitor.management")
    commands = parser.add_subparsers(dest="command", required=True)
    create_user = commands.add_parser("create-user", help="Create a user account")
    create_user.add_argument("--username", required=True)
    create_user.add_argument("--role", required=True, choices=[role.value for role in UserRole])
    create_user.add_argument("--astronaut-id", type=int, default=None, help="Required for the astronaut role")
    return parser


def create_user_from_command_line(arguments: Sequence[str], password: str | None = None) -> int:
    """Returns a process exit code. `password` is for tests; normally it is typed in."""
    parsed = build_parser().parse_args(arguments)
    settings = get_application_settings()
    configure_field_encryption(
        FieldEncryptor(load_or_create_encryption_key(settings.encryption_key, Path(settings.encryption_key_file)))
    )
    engine = create_database_engine(settings.database_url)
    create_all_tables(engine)
    if password is None:
        password = getpass.getpass("Password (8+ characters, upper and lower case, one special character): ")
        if getpass.getpass("Repeat password: ") != password:
            print("The passwords do not match.", file=sys.stderr)
            return 1
    with create_session_factory(engine)() as session:
        audit_service = AuditService(AuditRepository(session))
        service = AuthenticationService(UserRepository(session), AstronautRepository(session), audit_service)
        try:
            user = service.create_user(parsed.username, password, UserRole(parsed.role), parsed.astronaut_id)
        except AstronautHealthMonitorError as error:
            print(f"Could not create the user: {error}", file=sys.stderr)
            return 1
        audit_service.record(
            "user.created", AuditOutcome.SUCCESS, username="command-line", target=f"user:{user.username}"
        )
    print(f"Created {parsed.role} account {user.username!r}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(create_user_from_command_line(sys.argv[1:]))
