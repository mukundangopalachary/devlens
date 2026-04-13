# DevLens TUI Usage

Start TUI from repo root:

- `uv run devlens tui`

You do **not** need to run `go run .` manually anymore.

## Keybindings

- `tab` / `shift+tab`: change active pane
- `q`: quit
- `?` or `f1`: toggle help
- `ctrl+r`: refresh tasks + skills + sessions
- `ctrl+s`: open session picker
- `ctrl+o`: open ingest picker (type file path, Enter)
- `enter` in chat pane: send chat message

## Common Flows

1. Open TUI: `uv run devlens tui`
2. Press `ctrl+r` once after launch to sync all panes.
3. Chat:
   - ensure chat pane focused
   - type text
   - press `enter`
4. Ingest file:
   - press `ctrl+o`
   - type path like `src/devlens/chat/service.py`
   - press `enter`
   - press `ctrl+r`
5. Pick session:
   - press `ctrl+s`
   - use up/down
   - press `enter`

## Why `sessions` command exists

`devlens sessions` is backend list endpoint for TUI session picker.
It lists available chat sessions with ids and timestamps.

## If panes are empty

- run migrations: `uv run alembic upgrade head`
- create data:
  - `uv run devlens analyze .`
  - `uv run devlens ask "hello"`
- reopen TUI and press `ctrl+r`
