#!/usr/bin/env python3
"""
Trello MCP server (single file, v1.4)

Exposes 13 Trello tools over MCP: whoami, list_boards, get_board, list_cards,
get_card, search, create_card, update_card, move_card, add_comment,
archive_card, create_list, create_board.

Design:
  * Compact, one-line-per-item replies to keep the model's context small.
    get_card is light by default; full_desc, full_checklists, comments=N and
    full_comments widen it on demand and the reply says when it is truncated.
  * No delete tool by design. Cards are only archived (reversible).
  * List names are resolved once and cached, so results read "list=Doing".
  * Transports: stdio (Claude Desktop, Codex, most local clients) and a
    stateless Streamable HTTP mode ("gpt-http", standard library only) for
    chat clients that need a remote URL. In HTTP mode the secret in the URL
    path is the only authentication (constant-time compare) and is never
    logged. Expose it only behind a tunnel you control.
  * Logging is limited to "tools/call <tool> ok|ERROR <ms>".

Credentials: TRELLO_API_KEY and TRELLO_TOKEN environment variables, or a
trello_credentials.json next to the script: {"api_key": "...", "token": "..."}.
Requires Python 3.10+ and mcp>=1.9,<2 (stdio mode only).

Run:
  python trello_mcp.py                                   # stdio
  python trello_mcp.py --transport gpt-http --port 8765  # HTTP, path /mcp/<secret>

Note: user-facing messages and tool texts are currently in Polish.
"""

from __future__ import annotations

import argparse
import hmac
import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

PATH_PREFIX = "/trello"  # optional mount prefix: a tunnel may serve this server under /trello (paths with the prefix also work)
SERVER_NAME = "Trello_MCP_v1_4_2026-10-08_18_25_autor_Claude_Anthropic_dla_Pawla"
BASE_URL = os.environ.get("TRELLO_BASE_URL", "https://api.trello.com/1").rstrip("/")
HERE = Path(__file__).resolve().parent
TIMEOUT_S = 30

CARD_FIELDS = "id,name,idList,due,dueComplete,closed,labels"
DESC_LIMIT = 1500
COMMENT_LIMIT = 300
COMMENTS_SHOWN = 5
COMMENTS_MAX = 1000
CHECK_ITEM_LIMIT = 80
CHECKLIST_NAME_LIMIT = 60

READ = ToolAnnotations(readOnlyHint=True, openWorldHint=True)
WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=True)
WRITE_IDEMPOTENT = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=True)


# --------------------------------------------------------------------------
# Dane logowania i klient HTTP
# --------------------------------------------------------------------------

def _load_credentials() -> tuple[str, str]:
    key = os.environ.get("TRELLO_API_KEY", "").strip()
    token = os.environ.get("TRELLO_TOKEN", "").strip()
    if key and token:
        return key, token
    path = Path(os.environ.get("TRELLO_CREDENTIALS_FILE", HERE / "trello_credentials.json"))
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Nie moge odczytac pliku z danymi Trello ({path.name}): {exc}") from exc
        key = key or str(data.get("api_key", "")).strip()
        token = token or str(data.get("token", "")).strip()
    if not key or not token:
        raise RuntimeError(
            "Brak danych logowania do Trello. Ustaw TRELLO_API_KEY i TRELLO_TOKEN "
            "albo utworz trello_credentials.json z polami api_key i token."
        )
    return key, token


def _request(method: str, path: str, params: Optional[dict] = None, body: Optional[dict] = None) -> Any:
    key, token = _load_credentials()
    clean = {k: v for k, v in (params or {}).items() if v is not None}
    clean = {k: (str(v).lower() if isinstance(v, bool) else v) for k, v in clean.items()}
    url = f"{BASE_URL}{path}"
    if clean:
        url += "?" + urllib.parse.urlencode(clean)
    data = None
    headers = {
        "Accept": "application/json",
        "Authorization": f'OAuth oauth_consumer_key="{key}", oauth_token="{token}"',
    }
    if body is not None:
        data = json.dumps({k: v for k, v in body.items() if v is not None}).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        raise ValueError(f"Trello odpowiedzialo {exc.code} na {method} {path}: {detail}") from None
    except urllib.error.URLError as exc:
        raise ValueError(f"Brak polaczenia z Trello ({method} {path}): {exc.reason}") from None
    return json.loads(raw) if raw else {}


# --------------------------------------------------------------------------
# Formatowanie: krotki tekst zamiast JSON
# --------------------------------------------------------------------------

def _short(text: Optional[str], limit: int) -> str:
    t = " ".join((text or "").split())
    return t if len(t) <= limit else t[: limit - 1] + "…"


def _when(iso: Optional[str]) -> Optional[str]:
    return iso[:16].replace("T", " ") + "Z" if iso else None


_LIST_NAMES: dict = {}


def _prime_lists(board_id: str) -> None:
    """Jednym zapytaniem zapamietuje nazwy wszystkich otwartych list tablicy."""
    try:
        for l in _request("GET", f"/boards/{board_id}/lists", {"filter": "all", "fields": "id,name"}):
            _LIST_NAMES[l["id"]] = l.get("name") or l["id"]
    except Exception:  # noqa: BLE001 - nazwy to dodatek, brak nie moze psuc wyniku
        pass


def _list_label(list_id: str) -> str:
    if list_id not in _LIST_NAMES:
        try:
            _LIST_NAMES[list_id] = _short(_request("GET", f"/lists/{list_id}", {"fields": "name"}).get("name"), 60) or list_id
        except Exception:  # noqa: BLE001
            return list_id
    return _LIST_NAMES[list_id]


def _card_line(c: dict) -> str:
    parts = [str(c.get("id")), _short(c.get("name"), 120)]
    if c.get("idList"):
        parts.append(f"lista={_list_label(c['idList'])}")
    if c.get("due"):
        parts.append(f"termin={_when(c['due'])}")
    if c.get("dueComplete"):
        parts.append("zrobione")
    labels = [l.get("name") or l.get("color") for l in c.get("labels", []) if l.get("name") or l.get("color")]
    if labels:
        parts.append("etyk=" + ",".join(labels))
    if c.get("closed"):
        parts.append("ARCHIWUM")
    return " | ".join(parts)


def _cards_text(cards: list, limit: int, hint: str = "zwieksz limit") -> str:
    if not cards:
        return "0 kart"
    shown = cards[:limit]
    lines = [f"{len(cards)} kart" + (f" (pokazuje {len(shown)})" if len(cards) > len(shown) else "")]
    lines += [_card_line(c) for c in shown]
    if len(cards) > len(shown):
        lines.append(f"+{len(cards) - len(shown)} pominieto ({hint})")
    return "\n".join(lines)


def _cap(n: int, default: int, maximum: int) -> int:
    try:
        n = int(n)
    except (TypeError, ValueError):
        n = default
    return max(1, min(n, maximum))


# --------------------------------------------------------------------------
# Serwer MCP
# --------------------------------------------------------------------------

mcp = FastMCP(
    SERVER_NAME,
    instructions=(
        "Trello. Kolejnosc: trello_list_boards -> trello_get_board (listy i etykiety) -> "
        "trello_list_cards. Odpowiedzi sa celowo krotkie (jedna linia na element); "
        "pelna tresc karty tylko przez trello_get_card z full_desc, full_checklists, full_comments, comments=N. "
        "Nie ma kasowania, tylko archiwizacja."
    ),
)


@mcp.tool(annotations=READ, structured_output=False)
def trello_whoami() -> str:
    """Sprawdza klucz i token: zwraca konto Trello."""
    m = _request("GET", "/members/me", {"fields": "username,fullName"})
    return f"{m.get('username')} | {m.get('fullName')}"


@mcp.tool(annotations=READ, structured_output=False)
def trello_list_boards(include_closed: bool = False, limit: int = 50) -> str:
    """Tablice konta, jedna linia: id | nazwa."""
    limit = _cap(limit, 50, 200)
    boards = _request("GET", "/members/me/boards", {"fields": "id,name,closed", "filter": "all" if include_closed else "open"})
    lines = [f"{len(boards)} tablic"] + [f"{b['id']} | {_short(b.get('name'), 100)}" + (" | ARCHIWUM" if b.get("closed") else "") for b in boards[:limit]]
    if len(boards) > limit:
        lines.append(f"+{len(boards) - limit} pominieto (zwieksz limit)")
    return "\n".join(lines)


@mcp.tool(annotations=READ, structured_output=False)
def trello_get_board(board_id: str) -> str:
    """Listy (kolumny) i etykiety tablicy; stad biora sie id do tworzenia i przenoszenia kart."""
    board = _request("GET", f"/boards/{board_id}", {"fields": "name"})
    lists = _request("GET", f"/boards/{board_id}/lists", {"filter": "open", "fields": "id,name"})
    labels = _request("GET", f"/boards/{board_id}/labels", {"fields": "id,name,color", "limit": 100})
    for l in lists:
        _LIST_NAMES[l["id"]] = l.get("name") or l["id"]
    lines = [f"Tablica: {_short(board.get('name'), 100)}", "Listy:"]
    lines += [f"  {l['id']} | {_short(l.get('name'), 80)}" for l in lists] or ["  (brak)"]
    named = [l for l in labels if l.get("name") or l.get("color")]
    if named:
        lines.append("Etykiety:")
        lines += [f"  {l['id']} | {l.get('name') or '(bez nazwy)'}" + (f" ({l['color']})" if l.get("color") else "") for l in named]
    return "\n".join(lines)


@mcp.tool(annotations=READ, structured_output=False)
def trello_list_cards(list_id: Optional[str] = None, board_id: Optional[str] = None, include_archived: bool = False, limit: int = 30) -> str:
    """Karty z listy (list_id) albo z tablicy (board_id), jedna linia na karte, bez opisow. Podaj dokladnie jedno id."""
    if bool(list_id) == bool(board_id):
        raise ValueError("Podaj dokladnie jedno: list_id albo board_id.")
    limit = _cap(limit, 30, 200)
    if board_id:
        _prime_lists(board_id)
    path = f"/lists/{list_id}/cards" if list_id else f"/boards/{board_id}/cards"
    cards = _request("GET", path, {"filter": "all" if include_archived else "open", "fields": CARD_FIELDS})
    return _cards_text(cards, limit)


@mcp.tool(annotations=READ, structured_output=False)
def trello_get_card(card_id: str, full_desc: bool = False, full_checklists: bool = False, comments: int = COMMENTS_SHOWN, full_comments: bool = False) -> str:
    """Karta: podsumowanie, opis, checklisty, komentarze. Domyslnie skrocone (opis 1500 znakow, pozycje checklist 80, 5 komentarzy po 300 znakow); flagi full_* i comments=N daja calosc."""
    n_comments = max(0, min(int(comments), COMMENTS_MAX)) if comments is not None else COMMENTS_SHOWN
    c = _request("GET", f"/cards/{card_id}", {"fields": CARD_FIELDS + ",desc,shortUrl", "checklists": "all", "checklist_fields": "name"})
    acts = _request("GET", f"/cards/{card_id}/actions", {"filter": "commentCard", "limit": n_comments}) if n_comments else []
    lines = [_card_line(c)]
    if c.get("shortUrl"):
        lines.append(f"url: {c['shortUrl']}")
    desc = (c.get("desc") or "").strip()
    if desc:
        if full_desc:
            lines.append("opis:\n" + desc)
        else:
            lines.append("opis: " + _short(desc, DESC_LIMIT) + (" [skrocono, full_desc=true da calosc]" if len(" ".join(desc.split())) > DESC_LIMIT else ""))
    clipped = False
    for cl in c.get("checklists", []):
        parts = []
        for i in cl.get("checkItems", []):
            raw = " ".join((i.get("name") or "").split())
            if not full_checklists and len(raw) > CHECK_ITEM_LIMIT:
                clipped = True
            parts.append(("[x] " if i.get("state") == "complete" else "[ ] ") + (raw if full_checklists else _short(raw, CHECK_ITEM_LIMIT)))
        cl_name = " ".join((cl.get("name") or "").split())
        if not full_checklists and len(cl_name) > CHECKLIST_NAME_LIMIT:
            clipped = True
        lines.append(f"checklista {cl_name if full_checklists else _short(cl_name, CHECKLIST_NAME_LIMIT)}: {'; '.join(parts) or '(pusta)'}")
    if clipped:
        lines.append("[pozycje checklist skrocone, full_checklists=true da calosc]")
    if acts:
        lines.append(f"komentarze (ostatnie {len(acts)}):")
        text_clipped = False
        for a in acts:
            who = (a.get("memberCreator") or {}).get("fullName") or "?"
            raw = " ".join(str((a.get("data") or {}).get("text") or "").split())
            if not full_comments and len(raw) > COMMENT_LIMIT:
                text_clipped = True
            lines.append(f"  {(a.get('date') or '')[:10]} {who}: {raw if full_comments else _short(raw, COMMENT_LIMIT)}")
        if text_clipped:
            lines.append("[tresc komentarzy skrocona, full_comments=true da calosc]")
        if len(acts) >= n_comments and n_comments < COMMENTS_MAX:
            lines.append(f"[moze byc wiecej komentarzy, podnies comments (teraz {n_comments}, maks. {COMMENTS_MAX})]")
    return "\n".join(lines)


@mcp.tool(annotations=READ, structured_output=False)
def trello_search(query: str, limit: int = 10) -> str:
    """Szuka kart (skladnia wyszukiwarki Trello, np. 'faktura @ja -label:gotowe'). Domyslnie 10 wynikow, max 25."""
    limit = _cap(limit, 10, 25)
    res = _request("GET", "/search", {"query": query, "modelTypes": "cards", "cards_limit": limit, "card_fields": CARD_FIELDS})
    return _cards_text(res.get("cards", []), limit)


@mcp.tool(annotations=WRITE, structured_output=False)
def trello_create_card(list_id: str, name: str, desc: str = "", due: Optional[str] = None, label_ids: Optional[list[str]] = None, position: str = "bottom") -> str:
    """Tworzy karte. due: ISO 8601 (np. 2026-10-15T12:00:00+02:00). position: top lub bottom."""
    if position not in ("top", "bottom"):
        raise ValueError("position musi byc 'top' albo 'bottom'.")
    body = {"idList": list_id, "name": name, "desc": desc or None, "due": due, "idLabels": ",".join(label_ids) if label_ids else None, "pos": position}
    return "Utworzono: " + _card_line(_request("POST", "/cards", body=body))


@mcp.tool(annotations=WRITE_IDEMPOTENT, structured_output=False)
def trello_update_card(card_id: str, name: Optional[str] = None, desc: Optional[str] = None, due: Optional[str] = None, due_complete: Optional[bool] = None) -> str:
    """Zmienia nazwe, opis, termin lub status wykonania. Pominiete pola zostaja bez zmian."""
    body = {"name": name, "desc": desc, "due": due, "dueComplete": due_complete}
    if all(v is None for v in body.values()):
        raise ValueError("Podaj co najmniej jedno pole do zmiany.")
    return "Zmieniono: " + _card_line(_request("PUT", f"/cards/{card_id}", body=body))


@mcp.tool(annotations=WRITE_IDEMPOTENT, structured_output=False)
def trello_move_card(card_id: str, list_id: str, position: str = "bottom") -> str:
    """Przenosi karte na inna liste. position: top lub bottom."""
    if position not in ("top", "bottom"):
        raise ValueError("position musi byc 'top' albo 'bottom'.")
    return "Przeniesiono: " + _card_line(_request("PUT", f"/cards/{card_id}", body={"idList": list_id, "pos": position}))


@mcp.tool(annotations=WRITE, structured_output=False)
def trello_add_comment(card_id: str, text: str) -> str:
    """Dodaje komentarz do karty."""
    a = _request("POST", f"/cards/{card_id}/actions/comments", body={"text": text})
    return f"Dodano komentarz {a.get('id')}"


@mcp.tool(annotations=WRITE_IDEMPOTENT, structured_output=False)
def trello_archive_card(card_id: str) -> str:
    """Archiwizuje karte (odwracalne w Trello, nic nie jest kasowane)."""
    return "Zarchiwizowano: " + _card_line(_request("PUT", f"/cards/{card_id}", body={"closed": True}))


@mcp.tool(annotations=WRITE, structured_output=False)
def trello_create_list(board_id: str, name: str, position: str = "bottom") -> str:
    """Dodaje liste (kolumne) do tablicy."""
    if position not in ("top", "bottom"):
        raise ValueError("position musi byc 'top' albo 'bottom'.")
    r = _request("POST", "/lists", body={"idBoard": board_id, "name": name, "pos": position})
    return f"Utworzono liste: {r.get('id')} | {_short(r.get('name'), 80)}"


@mcp.tool(annotations=WRITE, structured_output=False)
def trello_create_board(name: str, desc: str = "", default_lists: bool = False) -> str:
    """Tworzy tablice. default_lists=true dodaje domyslne listy."""
    r = _request("POST", "/boards", body={"name": name, "desc": desc or None, "defaultLists": default_lists})
    return f"Utworzono tablice: {r.get('id')} | {_short(r.get('name'), 100)}"


# --------------------------------------------------------------------------
# Tryb dla ChatGPT (czat): reczny, bezstanowy Streamable HTTP
# Receptura sprawdzona w OpenFill: POST /mcp/<sekret>, zwykly JSON-RPC,
# odpowiedzi application/json, bez sesji, schematy pisane recznie.
# --------------------------------------------------------------------------

KNOWN_PROTOCOLS = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")
DEFAULT_PROTOCOL = "2025-06-18"
MAX_BODY = 1_000_000
GPT_INSTRUCTIONS = (
    "Trello access. Start with trello_list_boards, then trello_get_board for list and label ids, "
    "then trello_list_cards. Replies are short on purpose: one line per item. "
    "Use trello_get_card for details; add full_desc, full_checklists, full_comments and comments=N only when the complete text is needed. "
    "There is no delete tool; trello_archive_card only archives."
)


def _truthy(v: Any) -> bool:
    return str(v).strip().lower() in ("1", "true", "yes", "tak")


def _opt_bool(v: Any) -> Optional[bool]:
    return None if v in (None, "") else _truthy(v)


def _int(a: dict, key: str, default: int) -> int:
    try:
        return int(a.get(key))
    except (TypeError, ValueError):
        return default


def _str(a: dict, key: str) -> Optional[str]:
    v = a.get(key)
    return None if v in (None, "") else str(v)


def _s(desc: str) -> dict:
    return {"type": "string", "description": desc}


def _i(desc: str) -> dict:
    return {"type": "integer", "description": desc}


_BOOL_NOTE = " Pass the text true or false."
_POS = _s("top or bottom. Default bottom.")

GPT_TOOLS: list[dict] = [
    {
        "name": "trello_whoami", "ro": True, "idem": True,
        "description": "Check that the Trello connection works. Returns the account name. Call it first if any other Trello tool fails.",
        "props": {}, "required": [],
        "run": lambda a: trello_whoami(),
    },
    {
        "name": "trello_list_boards", "ro": True, "idem": True,
        "description": "List the user's open Trello boards, one line each: id | name. Call this first to get a board id, then call trello_get_board.",
        "props": {"include_closed": _s("Include archived boards." + _BOOL_NOTE), "limit": _i("Maximum boards to show. Default 50.")},
        "required": [],
        "run": lambda a: trello_list_boards(_truthy(a.get("include_closed", "false")), _int(a, "limit", 50)),
    },
    {
        "name": "trello_get_board", "ro": True, "idem": True,
        "description": "Get the lists (columns) and labels of one board, one line each with its id. Call this before creating or moving cards, because list_id and label ids come from here.",
        "props": {"board_id": _s("Board id from trello_list_boards.")}, "required": ["board_id"],
        "run": lambda a: trello_get_board(str(a["board_id"])),
    },
    {
        "name": "trello_list_cards", "ro": True, "idem": True,
        "description": "List cards of one list (list_id) or of a whole board (board_id), one short line per card, no descriptions. Give exactly one of list_id or board_id. Output is capped (default 30 cards); raise limit to see more. Use trello_get_card for the details of one card.",
        "props": {
            "list_id": _s("List id from trello_get_board."),
            "board_id": _s("Board id from trello_list_boards. Use instead of list_id to get all cards of the board."),
            "include_archived": _s("Include archived cards." + _BOOL_NOTE),
            "limit": _i("Maximum cards to show. Default 30, maximum 200."),
        },
        "required": [],
        "run": lambda a: trello_list_cards(_str(a, "list_id"), _str(a, "board_id"), _truthy(a.get("include_archived", "false")), _int(a, "limit", 30)),
    },
    {
        "name": "trello_get_card", "ro": True, "idem": True,
        "description": "Get one card: summary line, description, checklists and comments. By default it is short: description cut at 1500 characters, checklist items at 80, the 5 latest comments at 300 characters each, and the reply says when something was cut. For the complete text set full_desc, full_checklists and full_comments to true, and raise comments (up to 1000) to get more than 5 comments.",
        "props": {
            "card_id": _s("Card id from trello_list_cards or trello_search."),
            "full_desc": _s("Return the complete description." + _BOOL_NOTE),
            "full_checklists": _s("Return the complete text of every checklist item and checklist name." + _BOOL_NOTE),
            "comments": _i("How many latest comments to return. Default 5, maximum 1000, 0 for none."),
            "full_comments": _s("Return the complete text of each comment." + _BOOL_NOTE),
        },
        "required": ["card_id"],
        "run": lambda a: trello_get_card(str(a["card_id"]), _truthy(a.get("full_desc", "false")), _truthy(a.get("full_checklists", "false")), _int(a, "comments", COMMENTS_SHOWN), _truthy(a.get("full_comments", "false"))),
    },
    {
        "name": "trello_search", "ro": True, "idem": True,
        "description": "Search cards by text using Trello search syntax (for example: invoice @me -label:done). Returns at most 10 cards by default, one line each. Use it when the board or list is not known.",
        "props": {"query": _s("Search text."), "limit": _i("Maximum cards. Default 10, maximum 25.")}, "required": ["query"],
        "run": lambda a: trello_search(str(a["query"]), _int(a, "limit", 10)),
    },
    {
        "name": "trello_create_card", "ro": False, "idem": False,
        "description": "Create a card on a list. Get list_id (and label ids) from trello_get_board first. Returns one confirmation line with the new card id.",
        "props": {
            "list_id": _s("List id from trello_get_board."),
            "name": _s("Card title."),
            "desc": _s("Card description. Optional."),
            "due": _s("Due date as ISO 8601, for example 2026-10-15T12:00:00+02:00. Optional."),
            "label_ids": _s("Comma-separated label ids from trello_get_board. Optional."),
            "position": _POS,
        },
        "required": ["list_id", "name"],
        "run": lambda a: trello_create_card(
            str(a["list_id"]), str(a["name"]), a.get("desc") or "", _str(a, "due"),
            [x.strip() for x in str(a["label_ids"]).split(",") if x.strip()] if a.get("label_ids") else None,
            str(a.get("position") or "bottom"),
        ),
    },
    {
        "name": "trello_update_card", "ro": False, "idem": True,
        "description": "Change the title, description, due date or done status of a card. Only the fields you pass are changed.",
        "props": {
            "card_id": _s("Card id."), "name": _s("New title. Optional."), "desc": _s("New description. Optional."),
            "due": _s("New due date as ISO 8601. Optional."), "due_complete": _s("Mark the due date done or not done." + _BOOL_NOTE + " Optional."),
        },
        "required": ["card_id"],
        "run": lambda a: trello_update_card(str(a["card_id"]), _str(a, "name"), a.get("desc") if "desc" in a else None, _str(a, "due"), _opt_bool(a.get("due_complete"))),
    },
    {
        "name": "trello_move_card", "ro": False, "idem": True,
        "description": "Move a card to another list (same board or another board). Get list_id from trello_get_board.",
        "props": {"card_id": _s("Card id."), "list_id": _s("Target list id."), "position": _POS},
        "required": ["card_id", "list_id"],
        "run": lambda a: trello_move_card(str(a["card_id"]), str(a["list_id"]), str(a.get("position") or "bottom")),
    },
    {
        "name": "trello_add_comment", "ro": False, "idem": False,
        "description": "Add a comment to a card. Returns one confirmation line.",
        "props": {"card_id": _s("Card id."), "text": _s("Comment text.")}, "required": ["card_id", "text"],
        "run": lambda a: trello_add_comment(str(a["card_id"]), str(a["text"])),
    },
    {
        "name": "trello_archive_card", "ro": False, "idem": True,
        "description": "Archive a card. This is reversible in Trello and nothing is deleted. There is no delete tool.",
        "props": {"card_id": _s("Card id.")}, "required": ["card_id"],
        "run": lambda a: trello_archive_card(str(a["card_id"])),
    },
    {
        "name": "trello_create_list", "ro": False, "idem": False,
        "description": "Add a list (column) to a board. Returns one confirmation line with the new list id.",
        "props": {"board_id": _s("Board id."), "name": _s("List name."), "position": _POS}, "required": ["board_id", "name"],
        "run": lambda a: trello_create_list(str(a["board_id"]), str(a["name"]), str(a.get("position") or "bottom")),
    },
    {
        "name": "trello_create_board", "ro": False, "idem": False,
        "description": "Create a new board. Returns one confirmation line with the new board id.",
        "props": {"name": _s("Board name."), "desc": _s("Board description. Optional."), "default_lists": _s("Create the default lists (To Do, Doing, Done)." + _BOOL_NOTE)},
        "required": ["name"],
        "run": lambda a: trello_create_board(str(a["name"]), a.get("desc") or "", _truthy(a.get("default_lists", "false"))),
    },
]
GPT_INDEX = {t["name"]: t for t in GPT_TOOLS}


def _gpt_tools_list() -> list[dict]:
    return [
        {
            "name": t["name"],
            "description": t["description"],
            "inputSchema": {"type": "object", "properties": t["props"], "required": t["required"], "additionalProperties": False},
            "annotations": {"readOnlyHint": t["ro"], "destructiveHint": False, "idempotentHint": t["idem"], "openWorldHint": True},
        }
        for t in GPT_TOOLS
    ]


def _gpt_text(text: str, is_error: bool = False) -> dict:
    return {"content": [{"type": "text", "text": text}], "isError": is_error}


def _gpt_call(name: Any, args: Any) -> dict:
    tool = GPT_INDEX.get(name)
    if tool is None:
        return _gpt_text(f"Unknown tool: {name}. Call tools/list to see the available tools.", True)
    if not isinstance(args, dict):
        args = {}
    missing = [k for k in tool["required"] if args.get(k) in (None, "")]
    if missing:
        return _gpt_text("Missing required argument(s): " + ", ".join(missing), True)
    try:
        return _gpt_text(tool["run"](args))
    except (ValueError, RuntimeError) as exc:
        return _gpt_text(str(exc), True)
    except Exception as exc:  # noqa: BLE001
        return _gpt_text(f"Internal error in {name}: {type(exc).__name__}", True)


def _rpc_error(mid: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": message}}


def _gpt_rpc(msg: Any) -> Optional[dict]:
    """Obsluga jednej wiadomosci JSON-RPC. Zwraca odpowiedz albo None (dla powiadomien)."""
    if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0":
        return _rpc_error(None, -32600, "Invalid Request")
    method = msg.get("method")
    mid = msg.get("id")
    params = msg.get("params") if isinstance(msg.get("params"), dict) else {}
    is_notification = "id" not in msg
    if method == "initialize":
        asked = params.get("protocolVersion")
        result = {
            "protocolVersion": asked if asked in KNOWN_PROTOCOLS else DEFAULT_PROTOCOL,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": SERVER_NAME, "version": "1.4"},
            "instructions": GPT_INSTRUCTIONS,
        }
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": _gpt_tools_list()}
    elif method == "tools/call":
        result = _gpt_call(params.get("name"), params.get("arguments"))
    elif isinstance(method, str) and method.startswith("notifications/"):
        return None
    else:
        return None if is_notification else _rpc_error(mid, -32601, f"Method not found: {method}")
    return None if is_notification else {"jsonrpc": "2.0", "id": mid, "result": result}


def _gpt_secret() -> str:
    env = os.environ.get("TRELLO_MCP_SECRET", "").strip()
    if env:
        secret = env
    else:
        path = Path(os.environ.get("TRELLO_MCP_SECRET_FILE", HERE / "trello_mcp_secret.txt"))
        if path.is_file():
            secret = path.read_text(encoding="utf-8").strip()
        else:
            secret = secrets.token_urlsafe(24)
            path.write_text(secret, encoding="utf-8")
    if len(secret) < 16 or not all(c.isalnum() or c in "-_" for c in secret):
        raise RuntimeError("Sekret musi miec min. 16 znakow (litery, cyfry, - i _).")
    return secret


def _read_body(handler: BaseHTTPRequestHandler) -> bytes:
    if "chunked" in (handler.headers.get("Transfer-Encoding") or "").lower():
        chunks, total = [], 0
        while True:
            size = int((handler.rfile.readline().strip() or b"0").split(b";")[0], 16)
            if size == 0:
                handler.rfile.readline()
                break
            total += size
            if total > MAX_BODY:
                raise OverflowError
            chunks.append(handler.rfile.read(size))
            handler.rfile.readline()
        return b"".join(chunks)
    length = int(handler.headers.get("Content-Length") or 0)
    if length > MAX_BODY:
        raise OverflowError
    return handler.rfile.read(length)


def _make_handler(secret: str):
    expected_path = f"/mcp/{secret}"

    class GptHandler(BaseHTTPRequestHandler):
        server_version = "TrelloMCP/1.4"
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt, *args):  # nie logujemy sciezek (zawieraja sekret)
            pass

        def _reply(self, code: int, body: bytes = b"", extra: Optional[dict] = None):
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            if body:
                self.wfile.write(body)

        def _authorized(self) -> bool:
            p = self.path.split("?", 1)[0].encode()
            ok_plain = hmac.compare_digest(p, expected_path.encode())
            ok_prefixed = hmac.compare_digest(p, (PATH_PREFIX + expected_path).encode())
            return ok_plain or ok_prefixed

        def _not_post(self):
            if self._authorized():
                self._reply(405, b'{"error":"use POST"}', {"Allow": "POST"})
            else:
                self._reply(404, b'{"error":"not found"}')

        do_GET = do_PUT = do_DELETE = do_PATCH = do_OPTIONS = _not_post

        def do_POST(self):
            if not self._authorized():
                return self._reply(404, b'{"error":"not found"}')
            try:
                raw = _read_body(self)
            except OverflowError:
                return self._reply(413, b'{"error":"body too large"}')
            except (ValueError, OSError):
                return self._reply(400, b'{"error":"bad request"}')
            started = time.time()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                return self._reply(200, json.dumps(_rpc_error(None, -32700, "Parse error")).encode())
            if isinstance(msg, list):
                out = [r for r in (_gpt_rpc(m) for m in msg) if r is not None]
                if not out:
                    return self._reply(202)
                body = json.dumps(out, ensure_ascii=False).encode("utf-8")
            else:
                out = _gpt_rpc(msg)
                if out is None:
                    return self._reply(202)
                body = json.dumps(out, ensure_ascii=False).encode("utf-8")
            if isinstance(msg, dict) and msg.get("method") == "tools/call":
                name = (msg.get("params") or {}).get("name")
                failed = bool((out or {}).get("result", {}).get("isError")) if isinstance(out, dict) else False
                print(f"[{time.strftime('%H:%M:%S')}] tools/call {name} {'ERROR' if failed else 'ok'} {int((time.time() - started) * 1000)} ms", file=sys.stderr, flush=True)
            self._reply(200, body)

    return GptHandler


# --------------------------------------------------------------------------
# Start
# --------------------------------------------------------------------------

def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Trello MCP v1.4 (Claude, 2026-10-08 18:25)")
    p.add_argument("--transport", choices=["stdio", "gpt-http"], default="stdio",
                   help="stdio: Claude Desktop, Codex. gpt-http: ChatGPT (czat) przez staly adres HTTPS, np. Tailscale Funnel")
    p.add_argument("--host", default="127.0.0.1", help="tylko dla gpt-http")
    p.add_argument("--port", type=int, default=8765, help="tylko dla gpt-http")
    args = p.parse_args(argv)

    if args.transport == "stdio":
        mcp.run(transport="stdio")
        return 0

    secret = _gpt_secret()
    srv = ThreadingHTTPServer((args.host, args.port), _make_handler(secret))
    srv.daemon_threads = True
    print(f"Trello MCP v1.4 (gpt-http) nasluchuje na {args.host}:{args.port}, sciezka /mcp/<sekret> (sekret w pliku)", file=sys.stderr, flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
