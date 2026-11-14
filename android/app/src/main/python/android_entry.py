"""Starts the whole health monitor server inside the phone app, on the phone only (127.0.0.1)."""

import os
import threading
import traceback

_error = ""


def start(files_dir: str) -> None:
    global _error
    prefix = "ASTRONAUT_HEALTH_MONITOR_"
    os.environ[prefix + "DATABASE_URL"] = f"sqlite:///{files_dir}/astronaut_health_monitor.db"
    os.environ[prefix + "ENCRYPTION_KEY_FILE"] = f"{files_dir}/.data_encryption_key"
    os.environ[prefix + "DEMO_MODE"] = "true"

    def run() -> None:
        global _error
        try:
            import uvicorn

            from astronaut_health_monitor.api.application import create_application

            server = uvicorn.Server(
                uvicorn.Config(create_application(), host="127.0.0.1", port=8000, log_level="warning", loop="asyncio")
            )
            server.run()
        except BaseException:  # shown on the phone screen so a failure can be diagnosed
            _error = traceback.format_exc()

    threading.Thread(target=run, daemon=True).start()


def last_error() -> str:
    return _error
