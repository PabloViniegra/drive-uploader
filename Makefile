SHELL := /bin/bash

.PHONY: help install run lint test build clean

help:
	@echo "install  - sync dependencies (uv sync)"
	@echo "run      - start the uploader (loads .env)"
	@echo "lint     - run ruff check"
	@echo "test     - run pytest"
	@echo "build    - build a single-file binary for the host OS via PyInstaller"
	@echo "clean    - remove __pycache__, local db, and build artifacts"

install:
	uv sync

run:
	source .env && PYTHONPATH=src uv run python -m bootstrap.main

lint:
	uv run ruff check .

test:
	uv run pytest -q

build:
	uv run pyinstaller drive-uploader.spec

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	rm -f drive_uploader.db
	rm -rf build/build dist
