.PHONY: install lint type-check test build clean

install:
	pip install -e ".[dev]"

lint:
	ruff check --fix src/ tests/
	ruff format src/ tests/

type-check:
	mypy src/

test:
	pytest tests/ -v

build:
	pip install build
	python -m build

clean:
	rm -rf dist/ build/ *.egg-info src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
