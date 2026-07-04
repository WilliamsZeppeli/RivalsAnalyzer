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


def resolve_username(discord_id: int, provided: str | None) -> str | None:
    """Si el usuario no pasó un nombre, intenta usar el vinculado con /link."""
    if provided:
        return provided
    return storage.get_linked_account(discord_id)


@tree.command(name="link", description="Vincula tu cuenta de Discord con tu usuario de Marvel Rivals")
@app_commands.describe(usuario="Tu nombre de usuario en Marvel Rivals, ej: Sypeh#1234")
async def link(interaction: discord.Interaction, usuario: str):
    storage.link_account(interaction.user.id, usuario)
    await interaction.response.send_message(
        f"✅ Cuenta vinculada. A partir de ahora `/stats` y `/partidas` usarán **{usuario}** por defecto.",
        ephemeral=True,
    )


@tree.command(name="unlink", description="Elimina la vinculación de tu cuenta de Marvel Rivals")
async def unlink(interaction: discord.Interaction):
    storage.unlink_account(interaction.user.id)
    await interaction.response.send_message("🗑️ Vinculación eliminada.", ephemeral=True)


@tree.command(name="stats", description="Muestra tus stats de Marvel Rivals y retroalimentación de IA")
@app_commands.describe(usuario="Nombre de usuario o ID en Marvel Rivals (opcional si ya usaste /link)")
async def stats(interaction: discord.Interaction, usuario: str | None = None):
    await interaction.response.defer(thinking=True)

    target = resolve_username(interaction.user.id, usuario)
    if not target:
        await interaction.followup.send(
            "No tengo un usuario vinculado. Usa `/stats usuario:<tu_id_o_nombre>` "
            "o vincula tu cuenta primero con `/link`."
        )
        return

    try:
        raw_stats = await marvel_client.get_player_stats(target)
    except MarvelRivalsAPIError as e:
        await interaction.followup.send(f"⚠️ {e}")
        return
    except Exception:
        logger.exception("Error inesperado consultando stats")
        await interaction.followup.send("⚠️ Ocurrió un error inesperado consultando la API de Marvel Rivals.")
        return

    summary = summarize_player_stats(raw_stats)

    try:
        analysis = feedback_engine.generate(target, summary)
    except Exception:
        logger.exception("Error generando retroalimentación con Gemini")
        await interaction.followup.send("⚠️ Obtuve tus stats pero fallé al generar el análisis con IA.")
        return

    embed = discord.Embed(
        title=f"📊 Stats de {target}",
        description=analysis,
        color=discord.Color.red(),
    )
    embed.set_footer(text="Datos vía MarvelRivalsAPI.com · Análisis generado con Gemini")
    await interaction.followup.send(embed=embed)


@tree.command(name="partidas", description="Analiza tus últimas partidas de Marvel Rivals")
@app_commands.describe(
    usuario="Nombre de usuario o ID en Marvel Rivals (opcional si ya usaste /link)",
    cantidad="Cuántas partidas recientes analizar (por defecto 10, máx 20)",
)
async def partidas(interaction: discord.Interaction, usuario: str | None = None, cantidad: int = 10):
    await interaction.response.defer(thinking=True)

    target = resolve_username(interaction.user.id, usuario)
    if not target:
        await interaction.followup.send(
            "No tengo un usuario vinculado. Usa `/partidas usuario:<tu_id_o_nombre>` "
            "o vincula tu cuenta primero con `/link`."
        )
        return

    cantidad = max(1, min(cantidad, 20))

    try:
        raw_history = await marvel_client.get_match_history(target, limit=cantidad)
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
        analysis = feedback_engine.generate(target, {"recent_matches": matches})
    except Exception:
        logger.exception("Error generando retroalimentación con Gemini")
        await interaction.followup.send("⚠️ Obtuve tu historial pero fallé al generar el análisis con IA.")
        return

    embed = discord.Embed(
        title=f"🎮 Últimas {len(matches)} partidas de {target}",
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
