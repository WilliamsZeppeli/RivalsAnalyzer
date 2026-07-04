"""
Guarda en un archivo JSON local la relación discord_user_id -> cuenta de Marvel Rivals
(nombre + uid) para que la gente no tenga que escribir su nombre cada vez.

Para producción real con muchos usuarios, cambia esto por una base de datos
(SQLite, Postgres, etc.), pero para un bot personal/de servidor chico esto basta.
"""

import json
from pathlib import Path

DATA_FILE = Path(__file__).parent / "data" / "linked_accounts.json"


def _load() -> dict:
    if not DATA_FILE.exists():
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data: dict) -> None:
    DATA_FILE.parent.mkdir(exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def link_account(discord_id: int, marvel_username: str, marvel_uid: str) -> None:
    data = _load()
    data[str(discord_id)] = {"username": marvel_username, "uid": marvel_uid}
    _save(data)


def get_linked_account(discord_id: int) -> dict | None:
    """Devuelve {'username': ..., 'uid': ...} o None si no hay cuenta vinculada."""
    return _load().get(str(discord_id))


def unlink_account(discord_id: int) -> None:
    data = _load()
    data.pop(str(discord_id), None)
    _save(data)
