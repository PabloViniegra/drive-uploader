import logging
import sys

from src.bootstrap.dependency_container import DependencyContainer
from src.bootstrap.init_config import WizardError, prepare_settings
from src.bootstrap.version_check import CURRENT_VERSION, announce_new_version_if_any
from src.shared.paths import config_dir


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        settings = prepare_settings(sys.stdin, sys.stdout, config_dir())
    except WizardError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)
    announce_new_version_if_any(CURRENT_VERSION)
    DependencyContainer(settings).start()


if __name__ == "__main__":
    main()