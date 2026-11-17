import signal
import time

from app.documents.service import process_document, reconcile_interrupted
from app.extraction.service import process_extraction, recover_terminal_extractions
from app.integrations.service import apply_submission, recover_interrupted_submissions
from app.platform.database import session_factory
from app.platform.jobs import JobRegistry, run_once
from app.platform.logging import log
from app.platform.settings import get_settings


def build_registry() -> JobRegistry:
    registry = JobRegistry()
    registry.register_handler("document.process", process_document)
    registry.register_handler("extraction.process", process_extraction)
    registry.register_handler("submission.apply", apply_submission)
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
        with session_factory()() as session:
            reconcile_interrupted(session)
        with session_factory()() as session:
            recover_interrupted_submissions(session)
        with session_factory()() as session:
            recover_terminal_extractions(session)
        if not run_once(session_factory(), registry):
            time.sleep(1)


if __name__ == "__main__":
    main()
