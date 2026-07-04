"""
Guarda en un archivo JSON local qué nombre de usuario de Marvel Rivals
corresponde a cada usuario de Discord (usado por /link, /unlink y /stats).

NOTA sobre despliegues en Railway/Fly.io: el sistema de archivos de estos
hosts suele ser efímero — si no agregas un "Volume" persistente, este
archivo se puede borrar en cada redeploy. Para un bot personal/de un solo
servidor esto no suele ser grave (basta con volver a hacer /link), pero si
te importa que sobreviva a redeploys, agrega un volumen persistente y monta
esta carpeta ahí.
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


def link_account(discord_id: int, marvel_username: str) -> None:
    data = _load()
    data[str(discord_id)] = marvel_username
    _save(data)


def get_linked_account(discord_id: int) -> str | None:
    return _load().get(str(discord_id))


def unlink_account(discord_id: int) -> None:
    data = _load()
    data.pop(str(discord_id), None)
    _save(data)
