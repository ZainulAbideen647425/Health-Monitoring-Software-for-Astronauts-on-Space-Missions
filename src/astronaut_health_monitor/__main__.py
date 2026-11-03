"""Run the server with: python -m astronaut_health_monitor"""

import uvicorn

from astronaut_health_monitor.api.application import create_application


def main() -> None:
    uvicorn.run(create_application(), host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
