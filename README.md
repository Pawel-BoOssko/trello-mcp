# trello-mcp

A small, single-file [MCP](https://modelcontextprotocol.io) server for Trello, written for daily use by an AI agent that manages a large board (hundreds of cards) without flooding its own context.

## Why

The official connector loaded the client interface heavily (it rendered cards and other widgets in the UI), so this server was written as a lean replacement. Generic Trello integrations also return verbose JSON. With 100+ cards per board that burns context and money. This server is built around three constraints:

1. **Short replies.** One line per item, list names instead of ids, ids only where the next call needs them.
2. **Reversible writes only.** There is deliberately no delete tool: cards are archived, never destroyed.
3. **Works in both worlds.** stdio for local clients (Claude Desktop, Codex, most IDE clients) and a stateless Streamable HTTP mode for chat clients that require a remote URL.

## Tools (13)

Read: `trello_whoami`, `trello_list_boards`, `trello_get_board`, `trello_list_cards`, `trello_get_card`, `trello_search`
Write: `trello_create_card`, `trello_update_card`, `trello_move_card`, `trello_add_comment`, `trello_archive_card`, `trello_create_list`, `trello_create_board`

Every tool carries MCP annotations (read-only / idempotent / write) so clients can ask for confirmation sensibly.

`trello_get_card` is light by default and widens on request: `full_desc`, `full_checklists`, `comments=N` (1..1000, 0 = none), `full_comments`. The reply states when something is still truncated or when more comments exist than shown.

## Setup

```bash
pip install "mcp>=1.9,<2"          # needed for stdio mode only
export TRELLO_API_KEY=...          # https://trello.com/power-ups/admin
export TRELLO_TOKEN=...
python trello_mcp.py               # stdio
```

Credentials can also live in `trello_credentials.json` next to the script (`{"api_key": "...", "token": "..."}`); the file is git-ignored.

### HTTP mode (remote URL for chat clients)

```bash
python trello_mcp.py --transport gpt-http --port 8765
# endpoint: POST /mcp/<secret>
```

The secret is read from `TRELLO_MCP_SECRET` or a `trello_mcp_secret.txt` created on first start. It is the only authentication, so expose the port only behind a tunnel you control and treat the URL like a password. The secret is compared in constant time and never written to logs. This mode uses only the Python standard library, with hand-written strict tool schemas for clients that reject `$schema` or nested types.

## Operational notes

- Logging is limited to `tools/call <tool> ok|ERROR <ms>`: no arguments, no card content.
- List names are fetched once per process and cached.
- Messages returned to the model are currently in Polish.

## Status

Used daily against a live Trello workspace; tested against a mock API in both transports. No automated test suite in this repository yet.

## License

MIT