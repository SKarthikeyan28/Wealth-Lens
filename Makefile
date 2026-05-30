.PHONY: check lint types test

check: lint types test

lint:
	ruff check backend

types:
	mypy backend

test:
	pytest
