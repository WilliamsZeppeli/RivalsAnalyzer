"""
Cliente sencillo para MarvelRivalsAPI.com

Docs: https://docs.marvelrivalsapi.com/
Necesitas una API key gratuita, generada en https://marvelrivalsapi.com/
"""

import os
import aiohttp

BASE_URL = "https://marvelrivalsapi.com/api"


class MarvelRivalsAPIError(Exception):
    """Error genérico al hablar con la API de Marvel Rivals."""


class MarvelRivalsClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("MARVEL_RIVALS_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Falta MARVEL_RIVALS_API_KEY. Consigue una gratis en https://marvelrivalsapi.com/"
            )

    def _headers(self):
        return {"x-api-key": self.api_key}

    async def _get(self, path: str, params: dict | None = None):
        url = f"{BASE_URL}{path}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self._headers(), params=params) as resp:
                if resp.status == 404:
                    raise MarvelRivalsAPIError(
                        "No encontré a ese jugador. Revisa que el nombre de usuario esté "
                        "escrito exactamente igual que en el juego (mayúsculas/minúsculas incluidas)."
                    )
                if resp.status == 401:
                    raise MarvelRivalsAPIError(
                        "La API key de Marvel Rivals no es válida o no está configurada."
                    )
                if resp.status >= 400:
                    text = await resp.text()
                    raise MarvelRivalsAPIError(f"Error {resp.status} de la API: {text[:200]}")
                return await resp.json()

    async def find_player_uid(self, username: str) -> dict:
        """Busca el UID de un jugador a partir de su nombre de usuario."""
        return await self._get(f"/v1/find-player/{username}")

    async def get_player_stats(self, uid_or_username: str, season: str | None = None) -> dict:
        """Trae las estadísticas generales del jugador (rango, héroes, etc.)."""
        params = {"season": season} if season else None
        return await self._get(f"/v1/player/{uid_or_username}", params=params)

    async def get_match_history(
        self,
        uid_or_username: str,
        season: str | None = None,
        game_mode: str | None = None,
        page: int = 1,
        limit: int = 10,
    ) -> dict:
        """Trae el historial de partidas recientes del jugador."""
        params = {"page": page, "limit": limit}
        if season:
            params["season"] = season
        if game_mode:
            params["game_mode"] = game_mode
        return await self._get(f"/v2/player/{uid_or_username}/match-history", params=params)

    async def get_match_details(self, match_uid: str) -> dict:
        """Trae el detalle de una partida específica por su match_uid."""
        return await self._get(f"/v1/match/{match_uid}")
