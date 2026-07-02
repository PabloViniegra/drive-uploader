import logging

from src.bootstrap.dependency_container import DependencyContainer
from src.shared.config import load_settings


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    settings = load_settings()
    container = DependencyContainer(settings)
    container.start()


if __name__ == "__main__":
    main()
