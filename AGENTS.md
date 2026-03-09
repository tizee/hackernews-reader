# AGENTS.md

Instructions for AI coding agents working in this repository.

## Project Overview

- **Name**: hackernews-reader
- **Type**: cli-tool
- **Python**: >=3.10
- **Package Manager**: uv

## Commands

| Task | Command |
|------|---------|
| Install deps | `uv sync` |
| Run tests | `make test` or `uv run pytest tests/ -v` |
| Lint | `make lint` or `uv run ruff check src/ tests/` |
| Format | `make fmt` or `uv run ruff format src/ tests/` |
| Type check | `make typecheck` or `uv run pyright` |
| Install as global tool | `make install-tool` |

```bash
# Run a single test file / class / method
uv run pytest tests/test_client.py
uv run pytest tests/test_client.py::TestFetchStories
uv run pytest tests/test_client.py::TestFetchStories::test_fetches_top_stories
```

## Code Style

- **Formatter/Linter**: ruff (configured in pyproject.toml)
- **Type checker**: pyright in strict mode
- **Docstrings**: Google style
- **Quotes**: Single quotes (enforced by ruff formatter)
- **Line length**: 100 characters
- **Layout**: src-layout (`src/hn/`)

## Rules

- Use `uv` for all package operations -- never `pip install` directly
- Run `uv run ruff check` on any new or modified files before committing
- Run `uv run pyright` on edited files -- fix errors, avoid `# type: ignore` unless necessary
- No `print()` in library code -- use `logging`; `print()` is allowed in `cli.py` (T20 rule relaxed via per-file-ignores)
- All package code lives under `src/hn/`
- Tests go in `tests/` using pytest

## Architecture

Single-package Python CLI (`hn` command) that fetches Hacker News data and outputs markdown or JSON.

**Two API backends:**
- `client.py` -- HN Firebase API (`hacker-news.firebaseio.com/v0`) for real-time story lists, items, users, and updates. All fetches are async via `httpx.AsyncClient`.
- `algolia.py` -- Algolia HN Search API (`hn.algolia.com/api/v1`) for time-filtered and keyword searches. Activated when `--since` or `--keyword` is passed to the `stories` subcommand.

**Data flow:** CLI parser (`cli.py`) -> async command handler -> API client (`client.py` or `algolia.py`) -> dataclasses (`models.py`) -> formatters (`formatters.py`) -> stdout.

**Key design decisions:**
- `httpx.AsyncClient` is created per-command in `cli.py`, not shared globally. Each `cmd_*` function owns its client lifecycle.
- HTML in HN responses is stripped to plain text with markdown links preserved (`text.py:strip_html`).
- Comment trees are fetched recursively with a configurable depth limit (`client.py:_build_comment`). Deleted/dead comments are filtered out.
- `--json` serializes dataclasses via a custom default serializer using `dataclasses.asdict` (`formatters.py:_serialize`).

## Testing Patterns

- HTTP mocking uses `respx` (not `responses` or `unittest.mock` for HTTP). Apply `@respx.mock` decorator, then set up routes with `respx.get(...).respond(...)`.
- Async tests require `@pytest.mark.asyncio` on each test method (no global asyncio mode configured).
- Tests create their own `httpx.AsyncClient` instances directly (no shared fixtures).
