"""
Cliente sencillo para MRApi.org (por LunarAPI)

Docs: https://github.com/LunarAPI/api-docs
No requiere API key para los endpoints públicos usados aquí.

NOTA: Esta es una API no oficial hecha por la comunidad (igual que la
anterior que usábamos, marvelrivalsapi.com). Si en algún momento deja de
responder, revisa https://github.com/LunarAPI/api-docs o su Discord de
soporte para ver si cambió de dominio/formato.
"""

import aiohttp

BASE_URL = "https://mrapi.org/api"


class MarvelRivalsAPIError(Exception):
    """Error genérico al hablar con la API de Marvel Rivals."""


class MarvelRivalsClient:
    def __init__(self):
        pass  # no hace falta API key con mrapi.org

    async def _get(self, path: str, params: dict | None = None):
        url = f"{BASE_URL}{path}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                if resp.status == 404:
                    raise MarvelRivalsAPIError(
                        "No encontré a ese jugador. Revisa que el nombre de usuario esté "
                        "escrito exactamente igual que en el juego (mayúsculas/minúsculas incluidas)."
                    )
                if resp.status >= 400:
                    text = await resp.text()
                    raise MarvelRivalsAPIError(f"Error {resp.status} de la API: {text[:200]}")
                return await resp.json()

    async def find_player_uid(self, username: str) -> dict:
        """Busca el UID de un jugador a partir de su nombre de usuario."""
        data = await self._get(f"/player-id/{username}")
        # Normalizamos para que siempre tengamos 'name' y 'uid', sin importar
        # cómo se llamen exactamente los campos en la respuesta cruda.
        uid = data.get("id") or data.get("uid") or data.get("player_uid")
        if not uid:
            raise MarvelRivalsAPIError("No encontré a ese jugador (respuesta sin UID).")
        return {"name": data.get("name", username), "uid": str(uid)}

    async def get_player_stats(self, uid: str) -> dict:
        """Trae las estadísticas generales del jugador (rango, héroes, etc.) por UID."""
        return await self._get(f"/player/{uid}")

    async def get_match_history(self, uid: str, page: int = 1, **_ignored) -> dict:
        """Trae el historial de partidas recientes del jugador por UID."""
        return await self._get(f"/player-match/{uid}", params={"page": page})
