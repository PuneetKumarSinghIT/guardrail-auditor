import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

MODE = os.environ.get("MODE", "")


def main() -> None:
    logger.info(f"Starting ECS task MODE={MODE!r}")

    if MODE == "rules_engine":
        from src.handlers.rules_engine import main as run_rules_engine
        run_rules_engine()
    else:
        logger.error(f"Unknown or missing MODE env var: {MODE!r}. Expected: rules_engine")
        sys.exit(1)


if __name__ == "__main__":
    main()
