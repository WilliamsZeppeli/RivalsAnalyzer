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
    for key in ("name", "level", "rank", "rank_score", "region", "season"):
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


def summarize_match_history(raw: dict, max_matches: int = 10) -> list[dict]:
    """Extrae un resumen compacto de las últimas partidas."""
    matches = raw.get("matches") or raw.get("match_history") or raw.get("data") or []
    summary = []

    for match in matches[:max_matches]:
        summary.append(
            {
                "match_uid": match.get("match_uid"),
                "game_mode": match.get("game_mode"),
                "hero": match.get("hero_name") or match.get("cur_hero_id"),
                "result": "win" if match.get("is_win") else "loss",
                "kills": match.get("kills"),
                "deaths": match.get("deaths"),
                "assists": match.get("assists"),
                "damage": match.get("total_hero_damage"),
                "healing": match.get("total_hero_heal"),
                "damage_taken": match.get("total_damage_taken"),
            }
        )

    return summary
