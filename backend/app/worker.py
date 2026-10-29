import signal
import time

from app.platform.database import session_factory
from app.platform.jobs import HandlerUnavailableError, JobRegistry, run_once
from app.platform.logging import log
from app.platform.settings import get_settings


def unavailable_handler(session, resource_id):
    raise HandlerUnavailableError("Domain handler is not implemented")


def build_registry() -> JobRegistry:
    registry = JobRegistry()
    registry.register_handler("document.process", unavailable_handler)
    registry.register_handler("extraction.process", unavailable_handler)
    registry.register_handler("submission.apply", unavailable_handler)
    return registry


def main():
    get_settings()
    running = True

    def stop(signum, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    registry = build_registry()
    log("worker.started")
    while running:
        if not run_once(session_factory(), registry):
            time.sleep(1)


if __name__ == "__main__":
    main()
