# locg

Command-line interface for [League of Comic Geeks](https://leagueofcomicgeeks.com). Browse releases, search series, manage your collection, pull list, wish list, and read list.

All output is JSON, making it easy to pipe into `jq` or other tools.

## Installation

```bash
pip install .
# or
pipx install .
```

For development:

```bash
pip install -e ".[test]"
```

## Authentication

Some commands (collection, pull-list, wish-list, read-list, add, remove) require a League of Comic Geeks account.

```bash
locg login
```

This stores your session cookie in `~/.config/locg/cookies.json`.

## Commands

### search

Search for comic series by title.

```bash
locg search "batman"
locg search "amazing spider-man" --pretty
```

### releases

View new comic releases for a given week. Defaults to the current week (Wednesday is new comic day).

```bash
locg releases
locg releases --date 2026-04-02 --pretty
```

### comic

Get full details for a specific comic by ID (publisher, price, creators, description, etc.).

```bash
locg comic 9559460
locg comic 9559460 --pretty
```

### series

Get a series overview and its issue list.

```bash
locg series 149498
locg series 149498 --pretty
```

### collection

View your collected comics (requires login).

```bash
locg collection --pretty
```

### pull-list

View your pull list (requires login).

```bash
locg pull-list --pretty
```

### wish-list

View your wish list (requires login).

```bash
locg wish-list --pretty
```

### read-list

View your read list (requires login).

```bash
locg read-list --pretty
```

### add

Add a comic to a list (requires login). Lists: `pull`, `collection`, `wish`, `read`.

```bash
locg add collection 9559460
locg add pull 9559460
```

### remove

Remove a comic from a list (requires login). Lists: `pull`, `collection`, `wish`, `read`.

```bash
locg remove collection 9559460
locg remove wish 9559460
```

### login

Log in to League of Comic Geeks. Prompts for username and password.

```bash
locg login
```

## Global Flags

| Flag | Description |
|------|-------------|
| `--pretty` | Pretty-print JSON output with indentation |
| `--debug` | Print HTTP request/response debug info to stderr |
| `--version` | Show version and exit |

## Output Format

All commands output JSON. Errors are written to stderr as `{"error": "message"}`.

Example output for `locg search "batman" --pretty`:

```json
[
  {
    "id": 149498,
    "name": "Batman",
    "publisher": "DC Comics",
    "start_year": 2016,
    "end_year": 2020,
    "issue_count": 150,
    "cover_url": "https://...",
    "url": "https://leagueofcomicgeeks.com/comics/series/149498/batman"
  }
]
```

## Configuration

Config and cookies are stored in `~/.config/locg/` (respects `XDG_CONFIG_HOME`).

## License

MIT
