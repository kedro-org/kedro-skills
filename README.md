# kedro-skills

[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://pypi.org/project/kedro-skills/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

Distribute AI coding skills to Kedro projects.

## Installation

```bash
pip install kedro-skills
```

## Quick start

```bash
# Inside a Kedro project:
kedro skills --help
kedro skills list
```

## Development

```bash
pip install -e ".[dev]"
```

Run all checks:

```bash
ruff check src/ tests/ && ruff format --check src/ tests/ && mypy src/ && pytest tests/ -v
```
