"""
Bot de Discord: análisis de desempeño en Marvel Rivals.

Comandos:
  /analizar [texto] [imagen]  -> analiza tus stats generales (rango, héroes, etc.)
  /partidas [texto] [imagen1] [imagen2] [imagen3]  -> analiza tus últimas partidas

Puedes pasar texto pegado, una o varias capturas de pantalla, o ambos.
No depende de ninguna API externa de Marvel Rivals: Gemini lee las capturas
directamente (es multimodal), así que no hay ningún servicio de terceros
que se pueda caer y romper el bot.

Configura las variables de entorno en un archivo .env (ver .env.example):
  DISCORD_BOT_TOKEN
  GEMINI_API_KEY
"""

import logging
import os

import discord
from discord import app_commands
from dotenv import load_dotenv

from feedback import FeedbackEngine

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("marvel-rivals-bot")

DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

feedback_engine = FeedbackEngine()


async def _load_image(attachment: discord.Attachment | None) -> tuple[bytes, str] | None:
    """Descarga un adjunto de Discord y lo deja listo para mandarlo a Gemini."""
    if attachment is None:
        return None
    if not (attachment.content_type or "").startswith("image/"):
        raise ValueError(f"El archivo `{attachment.filename}` no parece ser una imagen.")
    data = await attachment.read()
    return data, attachment.content_type


@tree.command(name="analizar", description="Analiza tus stats generales de Marvel Rivals (texto y/o captura)")
@app_commands.describe(
    texto="Pega aquí tus stats como texto (opcional si subes una imagen)",
    imagen="Captura de pantalla de tu menú de stats (opcional si pegas texto)",
)
async def analizar(
    interaction: discord.Interaction,
    texto: str | None = None,
    imagen: discord.Attachment | None = None,
):
    await interaction.response.defer(thinking=True)

    if not texto and not imagen:
        await interaction.followup.send(
            "Necesito al menos un `texto` con tus stats o una `imagen` (captura de pantalla) para analizar."
        )
        return

    images = []
    try:
        loaded = await _load_image(imagen)
        if loaded:
            images.append(loaded)
    except ValueError as e:
        await interaction.followup.send(f"⚠️ {e}")
        return

    try:
        analysis = feedback_engine.generate(
            instruction=(
                "Analiza las siguientes estadísticas generales de Marvel Rivals "
                "(rango, héroes jugados, KDA, daño, healing, etc.) del usuario."
            ),
            text=texto,
            images=images,
        )
    except Exception:
        logger.exception("Error generando retroalimentación con Gemini")
        await interaction.followup.send("⚠️ Ocurrió un error generando el análisis con IA. Intenta de nuevo.")
        return

    embed = discord.Embed(
        title="📊 Análisis de tus stats",
        description=analysis,
        color=discord.Color.red(),
    )
    embed.set_footer(text="Análisis generado con Gemini")
    if imagen:
        embed.set_thumbnail(url=imagen.url)
    await interaction.followup.send(embed=embed)


@tree.command(name="partidas", description="Analiza tus últimas partidas de Marvel Rivals (texto y/o capturas)")
@app_commands.describe(
    texto="Pega aquí el resumen de tus últimas partidas como texto (opcional)",
    imagen1="Captura de pantalla de una partida (opcional)",
    imagen2="Otra captura de pantalla (opcional)",
    imagen3="Otra captura de pantalla más (opcional)",
)
async def partidas(
    interaction: discord.Interaction,
    texto: str | None = None,
    imagen1: discord.Attachment | None = None,
    imagen2: discord.Attachment | None = None,
    imagen3: discord.Attachment | None = None,
):
    await interaction.response.defer(thinking=True)

    adjuntos = [a for a in (imagen1, imagen2, imagen3) if a is not None]
    if not texto and not adjuntos:
        await interaction.followup.send(
            "Necesito al menos un `texto` con tus partidas o una imagen (captura de pantalla) para analizar."
        )
        return

    images = []
    try:
        for attachment in adjuntos:
            loaded = await _load_image(attachment)
            if loaded:
                images.append(loaded)
    except ValueError as e:
        await interaction.followup.send(f"⚠️ {e}")
        return

    try:
        analysis = feedback_engine.generate(
            instruction=(
                "Analiza el siguiente historial de partidas recientes de Marvel Rivals del usuario "
                "(resultado, héroe jugado, kills/deaths/assists, daño, healing, etc. de cada partida)."
            ),
            text=texto,
            images=images,
        )
    except Exception:
        logger.exception("Error generando retroalimentación con Gemini")
        await interaction.followup.send("⚠️ Ocurrió un error generando el análisis con IA. Intenta de nuevo.")
        return

    embed = discord.Embed(
        title=f"🎮 Análisis de tus últimas partidas",
        description=analysis,
        color=discord.Color.blue(),
    )
    embed.set_footer(text="Análisis generado con Gemini")
    await interaction.followup.send(embed=embed)


@client.event
async def on_ready():
    await tree.sync()
    logger.info(f"Bot conectado como {client.user}")


if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise SystemExit("Falta DISCORD_BOT_TOKEN en tu archivo .env")
    client.run(DISCORD_TOKEN)
