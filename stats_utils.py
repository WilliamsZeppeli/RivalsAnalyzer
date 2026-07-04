"""
Funciones para tomar la respuesta cruda de MarvelRivalsAPI.com y quedarnos
solo con lo relevante antes de mandarlo al modelo (ahorra tokens y ruido).

NOTA: La estructura exacta de la respuesta de la API puede cambiar con el
tiempo (es una API no oficial y en evolución). Si algo deja de funcionar,
imprime el JSON crudo (json.dumps(data, indent=2)) para ver los campos
reales y ajusta las funciones de abajo.
"""


def summarize_player_stats(raw: dict) -> dict:
    """Se queda con los campos más útiles del perfil general del jugador."""
    summary = {}

    # Campos típicos de nivel/rango — se guardan tal cual si existen
    for key in (
        "name", "player_name", "level", "rank", "rank_score",
        "region", "season", "player_uid",
    ):
        if key in raw:
            summary[key] = raw[key]

    # Stats generales (ajusta las llaves si la API las nombra distinto)
    overall = raw.get("overall_stats") or raw.get("stats")
    if overall:
        summary["overall_stats"] = overall

    # Top héroes jugados, si vienen en la respuesta
    heroes = raw.get("heroes") or raw.get("hero_stats")
    if heroes:
        # nos quedamos solo con los primeros N para no saturar el contexto
        summary["heroes"] = heroes[:10] if isinstance(heroes, list) else heroes

    return summary or raw  # si no reconocemos la forma, mandamos el raw completo


def summarize_match_history(raw, max_matches: int = 10) -> list[dict]:
    """Extrae un resumen compacto de las últimas partidas.

    mrapi.org puede devolver una lista directa de partidas, o un dict que
    envuelve la lista bajo alguna llave (match_history, matches, data...).
    Manejamos ambos casos para no quebrarnos si cambia el formato.
    """
    if isinstance(raw, list):
        matches = raw
    elif isinstance(raw, dict):
        matches = (
            raw.get("match_history")
            or raw.get("matches")
            or raw.get("data")
            or []
        )
    else:
        matches = []

    summary = []
    for match in matches[:max_matches]:
        # Algunos formatos anidan las stats del jugador bajo 'match_player'
        player_data = match.get("match_player", match)
        hero_data = player_data.get("player_hero", {})

        summary.append(
            {
                "match_uid": match.get("match_uid") or match.get("id"),
                "game_mode": match.get("game_mode_id") or match.get("game_mode"),
                "hero": hero_data.get("hero_name") or player_data.get("hero_name"),
                "result": "win" if player_data.get("is_win") else "loss",
                "kills": player_data.get("kills"),
                "deaths": player_data.get("deaths"),
                "assists": player_data.get("assists"),
                "damage": hero_data.get("total_hero_damage"),
                "healing": hero_data.get("total_hero_heal"),
                "damage_taken": hero_data.get("total_damage_taken"),
            }
        )

    return summary
