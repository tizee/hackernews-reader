# hackernews-reader

A CLI tool for fetching and reading Hacker News content. Outputs markdown or JSON.

Uses the [HN Firebase API](https://github.com/HackerNews/API) for real-time data and the [Algolia HN Search API](https://hn.algolia.com/api) for time-based and keyword searches.

## Installation

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/).

```bash
# Install as a global uv tool
make install-tool

# Or manually
uv tool install . --reinstall
```

This installs the `hn` command.

## Usage

All commands support `--json` for JSON output instead of markdown.

### Browse stories

```bash
# Top stories (default)
hn stories

# Specific types: top, new, best, ask, show, job
hn stories --type ask
hn stories --type show --limit 20
```

### Search stories (Algolia)

Use `--since` and/or `--keyword` to search via Algolia:

```bash
# Stories from the past 24 hours
hn stories --since 24h

# Stories from the past week about Rust
hn stories --since 7d --keyword rust

# Show HN posts from the past 3 days
hn stories --type show --since 3d --limit 5
```

Supported duration units: `m` (minutes), `h` (hours), `d` (days), `w` (weeks).

> Note: `--since`/`--keyword` are not supported with `--type job`.

### View a single item

```bash
# Basic item info
hn item 42424242

# With comment tree (default depth: 2)
hn item 42424242 --with-comments

# Deeper comment tree
hn item 42424242 --with-comments --comment-depth 5
```

### User profiles

```bash
hn user dang
```

### Recent updates

```bash
hn updates
```

### JSON output

```bash
hn --json stories --type best --limit 5
hn --json item 42424242 --with-comments
hn --json user dang
```

## Development

```bash
# Install dev dependencies
make install

# Run tests
make test

# Lint and format
make lint
make fmt

# Type check
make typecheck
```

## License

MIT
