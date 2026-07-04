"""
Bot de Discord: análisis de desempeño en Marvel Rivals.

Comandos:
  /link <usuario_marvel_rivals>   -> vincula tu cuenta de Discord con tu nombre en Marvel Rivals
  /stats [usuario_marvel_rivals]  -> muestra tus stats generales + retroalimentación de Gemini
  /partidas [usuario] [cantidad]  -> analiza tus últimas N partidas
  /unlink                         -> elimina la vinculación guardada

Configura las variables de entorno en un archivo .env (ver .env.example):
  DISCORD_BOT_TOKEN
  MARVEL_RIVALS_API_KEY
  GEMINI_API_KEY

Nota sobre nombres de usuario: la propia documentación de MarvelRivalsAPI.com
advierte que buscar stats/historial directamente por username no siempre es
confiable. Por eso este bot primero resuelve el nombre a un UID con el
endpoint find-player, y usa ese UID para todo lo demás.
"""

import os
import logging

import discord
from discord import app_commands
from dotenv import load_dotenv

from marvel_api import MarvelRivalsClient, MarvelRivalsAPIError
from feedback import FeedbackEngine
from stats_utils import summarize_player_stats, summarize_match_history
import storage

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("marvel-rivals-bot")

DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

marvel_client = MarvelRivalsClient()
feedback_engine = FeedbackEngine()


async def resolve_player(discord_id: int, provided: str | None):
    """
    Devuelve (nombre_para_mostrar, uid) listo para usar en las llamadas a la API,
    o (None, None) si no hay nada que usar.
    Si 'provided' viene, siempre lo resuelve contra find-player (para sacar el UID).
    Si no viene, usa la cuenta vinculada con /link (que ya trae el UID guardado).
    """
    if provided:
        result = await marvel_client.find_player_uid(provided)
        return result.get("name", provided), result.get("uid", provided)

    linked = storage.get_linked_account(discord_id)
    if linked:
        return linked["username"], linked["uid"]

    return None, None


@tree.command(name="link", description="Vincula tu cuenta de Discord con tu usuario de Marvel Rivals")
@app_commands.describe(usuario="Tu nombre de usuario exacto en Marvel Rivals")
async def link(interaction: discord.Interaction, usuario: str):
    await interaction.response.defer(thinking=True, ephemeral=True)

    try:
        result = await marvel_client.find_player_uid(usuario)
    except MarvelRivalsAPIError as e:
        await interaction.followup.send(f"⚠️ {e}", ephemeral=True)
        return
    except Exception:
        logger.exception("Error inesperado buscando jugador en /link")
        await interaction.followup.send("⚠️ Ocurrió un error inesperado consultando la API de Marvel Rivals.", ephemeral=True)
        return

    name = result.get("name", usuario)
    uid = result.get("uid")
    if not uid:
        await interaction.followup.send(
            "⚠️ Encontré una respuesta pero sin UID. Intenta de nuevo o revisa el nombre exacto.",
            ephemeral=True,
        )
        return

    storage.link_account(interaction.user.id, name, uid)
    await interaction.followup.send(
        f"✅ Cuenta vinculada. A partir de ahora `/stats` y `/partidas` usarán **{name}** por defecto.",
        ephemeral=True,
    )


@tree.command(name="unlink", description="Elimina la vinculación de tu cuenta de Marvel Rivals")
async def unlink(interaction: discord.Interaction):
    storage.unlink_account(interaction.user.id)
    await interaction.response.send_message("🗑️ Vinculación eliminada.", ephemeral=True)


@tree.command(name="stats", description="Muestra tus stats de Marvel Rivals y retroalimentación de IA")
@app_commands.describe(usuario="Nombre de usuario en Marvel Rivals (opcional si ya usaste /link)")
async def stats(interaction: discord.Interaction, usuario: str | None = None):
    await interaction.response.defer(thinking=True)

    try:
        name, uid = await resolve_player(interaction.user.id, usuario)
    except MarvelRivalsAPIError as e:
        await interaction.followup.send(f"⚠️ {e}")
        return

    if not uid:
        await interaction.followup.send(
            "No tengo un usuario vinculado. Usa `/stats usuario:<tu_nombre>` "
            "o vincula tu cuenta primero con `/link`."
        )
        return

    try:
        raw_stats = await marvel_client.get_player_stats(uid)
    except MarvelRivalsAPIError as e:
        await interaction.followup.send(f"⚠️ {e}")
        return
    except Exception:
        logger.exception("Error inesperado consultando stats")
        await interaction.followup.send("⚠️ Ocurrió un error inesperado consultando la API de Marvel Rivals.")
        return

    summary = summarize_player_stats(raw_stats)

    try:
        analysis = feedback_engine.generate(name, summary)
    except Exception:
        logger.exception("Error generando retroalimentación con Gemini")
        await interaction.followup.send("⚠️ Obtuve tus stats pero fallé al generar el análisis con IA.")
        return

    embed = discord.Embed(
        title=f"📊 Stats de {name}",
        description=analysis,
        color=discord.Color.red(),
    )
    embed.set_footer(text="Datos vía MarvelRivalsAPI.com · Análisis generado con Gemini")
    await interaction.followup.send(embed=embed)


@tree.command(name="partidas", description="Analiza tus últimas partidas de Marvel Rivals")
@app_commands.describe(
    usuario="Nombre de usuario en Marvel Rivals (opcional si ya usaste /link)",
    cantidad="Cuántas partidas recientes analizar (por defecto 10, máx 20)",
)
async def partidas(interaction: discord.Interaction, usuario: str | None = None, cantidad: int = 10):
    await interaction.response.defer(thinking=True)

    try:
        name, uid = await resolve_player(interaction.user.id, usuario)
    except MarvelRivalsAPIError as e:
        await interaction.followup.send(f"⚠️ {e}")
        return

    if not uid:
        await interaction.followup.send(
            "No tengo un usuario vinculado. Usa `/partidas usuario:<tu_nombre>` "
            "o vincula tu cuenta primero con `/link`."
        )
        return

    cantidad = max(1, min(cantidad, 20))

    try:
        raw_history = await marvel_client.get_match_history(uid, limit=cantidad)
    except MarvelRivalsAPIError as e:
        await interaction.followup.send(f"⚠️ {e}")
        return
    except Exception:
        logger.exception("Error inesperado consultando historial")
        await interaction.followup.send("⚠️ Ocurrió un error inesperado consultando la API de Marvel Rivals.")
        return

    matches = summarize_match_history(raw_history, max_matches=cantidad)
    if not matches:
        await interaction.followup.send("No encontré partidas recientes para ese usuario.")
        return

    try:
        analysis = feedback_engine.generate(name, {"recent_matches": matches})
    except Exception:
        logger.exception("Error generando retroalimentación con Gemini")
        await interaction.followup.send("⚠️ Obtuve tu historial pero fallé al generar el análisis con IA.")
        return

    embed = discord.Embed(
        title=f"🎮 Últimas {len(matches)} partidas de {name}",
        description=analysis,
        color=discord.Color.blue(),
    )
    embed.set_footer(text="Datos vía MarvelRivalsAPI.com · Análisis generado con Gemini")
    await interaction.followup.send(embed=embed)


@client.event
async def on_ready():
    await tree.sync()
    logger.info(f"Bot conectado como {client.user}")


if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise SystemExit("Falta DISCORD_BOT_TOKEN en tu archivo .env")
    client.run(DISCORD_TOKEN)
