.PHONY: install run lint test build
install:
	uv sync
run:
	uv run database
lint:
	uv run ruff check .
test:
	uv run python -m unittest discover -s tests -v
build:
	uv build
