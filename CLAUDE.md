# locg

CLI for [League of Comic Geeks](https://leagueofcomicgeeks.com). Scraping-based (no official API).

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

## Running

```bash
# Development (no install)
PYTHONPATH=src python3 -m locg <command>

# Installed
pip install -e .
locg <command>
```

## Testing

```bash
# Run all tests
PYTHONPATH=src python3 -m pytest tests/ -v

# Or with installed package
pip install -e ".[test]"
pytest tests/ -v
```

## Dependencies

- `curl-cffi` — HTTP client with browser impersonation (Cloudflare bypass)
- `beautifulsoup4` — HTML parsing
- `pytest` (test only)
