SHELL := /bin/bash

.PHONY: help install run lint test clean

help:
	@echo "install  - sync dependencies (uv sync)"
	@echo "run      - start the uploader (loads .env)"
	@echo "lint     - run ruff check"
	@echo "test     - run pytest"
	@echo "clean    - remove __pycache__ and local db"

install:
	uv sync

run:
	source .env && PYTHONPATH=src uv run python -m bootstrap.main

lint:
	uv run ruff check .

test:
	uv run pytest -q

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	rm -f drive_uploader.db
