# AI Platform

Production-ready Python CLI foundation for AI services.

## Requirements

- Python 3.14+
- pip

## Setup

```bash
python3.14 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp config/.env.example config/.env
```

## Usage

```bash
ai --help
python -m app.main --help
```

## Development

```bash
pytest
ruff check .
ruff format --check .
black --check .
```

## Project structure

```
app/
  main.py          # Typer CLI entry point
  core/            # Config, logging
  commands/        # CLI commands (future)
  services/        # Business services (future)
config/            # Environment templates
tests/             # Test suite
```
