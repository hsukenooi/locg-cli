# locg

CLI for [League of Comic Geeks](https://leagueofcomicgeeks.com). Scraping-based (no official API).

## CLI Usage

Run with `PYTHONPATH=src python3 -m locg <command>` (or `locg <command>` if installed).

All output is JSON to stdout. Use `--pretty` for human-readable output, `--debug` for HTTP details.

### Finding comics

```bash
# Search for a series by name — returns series ID, name, publisher, year
locg search "Batman"

# Get all issues in a series — returns issue IDs, names, dates
locg series <series_id>

# Get full details for a specific comic (creators, price, description)
locg comic <comic_id>

# This week's new releases (or a specific week)
locg releases
locg releases --date 2024-01-15
```

### Workflow: adding comics by name

Comic IDs are required for add/remove/check. To find a comic ID:
1. `locg search "<series name>"` — find the series ID
2. `locg series <series_id>` — find the issue ID in the series listing
3. `locg add collection <comic_id>` — add by issue ID

### Managing lists (requires login)

```bash
# View lists (collection, pull-list, wish-list, read-list)
locg collection
locg pull-list
locg wish-list
locg read-list

# Filter by title (case-insensitive substring match)
locg collection --title "batman"

# Add/remove a comic to/from a list (pull, collection, wish, read)
locg add collection <comic_id>
locg remove wish <comic_id>

# Check which lists a comic belongs to (accepts multiple IDs)
locg check <comic_id> [<comic_id> ...]
```

### Authentication

```bash
# Interactive login (prompts for credentials, persists session cookie)
locg login

# Non-interactive
locg login -u <username> -p <password>
```

Session cookies are stored at `~/.config/locg/cookies.json`. Sessions can expire server-side; if you get "Session expired", run `locg login` again.

## Architecture

```
src/locg/
├── __init__.py      # Package version
├── __main__.py      # `python -m locg` entry point
├── cli.py           # Argparse definitions, main() entry, JSON output
├── client.py        # HTTP client using curl_cffi (Cloudflare bypass), cookie persistence
├── commands.py      # Command implementations (search, releases, comic, series, lists, add/remove, login)
├── config.py        # XDG config dir management, cookie/config file paths
├── models.py        # HTML → dict extraction (extract_issue, extract_series, extract_comic_detail)
├── parser.py        # Low-level HTML/JSON parsing helpers (BeautifulSoup wrappers, price/date extraction)
```

- **client.py** handles all HTTP. Uses `curl_cffi` with Chrome impersonation to bypass Cloudflare. Session cookies are persisted to `~/.config/locg/cookies.json`.
- **commands.py** orchestrates client calls and parser/model extraction. Each `cmd_*` function returns a dict or list of dicts.
- **models.py** extracts structured data from BeautifulSoup tags. `extract_issue` handles list items, `extract_series` handles search results, `extract_comic_detail` handles full comic pages.
- **parser.py** provides shared parsing utilities (JSON list response parsing, text cleaning, price/date extraction).
- **cli.py** wires argparse to commands and handles JSON serialization, error formatting, and exit codes.

## Conventions

- Python 3.9+, type hints throughout, `from __future__ import annotations`
- All output is JSON to stdout; errors are JSON to stderr
- Exit codes: 0 success, 1 general error, 2 no command, 3 auth required, 4 unexpected error
- No third-party CLI framework (just argparse)

## Testing

```bash
PYTHONPATH=src python3 -m pytest tests/ -v
```

## Dependencies

- `curl-cffi` — HTTP client with browser impersonation (Cloudflare bypass)
- `beautifulsoup4` — HTML parsing
- `pytest` (test only)
