"""
Bot de Discord: análisis de desempeño en Marvel Rivals.

Comandos:
  /link <usuario>              -> vincula tu nombre de usuario del juego a tu cuenta de Discord
  /unlink                      -> elimina la vinculación guardada
  /stats <imagen> [usuario]    -> analiza TU desempeño en una partida (KDA, final hits, curación,
                                   daño, daño bloqueado) usando la cuenta vinculada o el usuario dado
  /game <imagen>               -> análisis imparcial de fortalezas/debilidades de TODOS los
                                   jugadores de la partida, sin enfocarse en nadie en particular
  /meta                        -> resumen del meta actual de la temporada vigente (con búsqueda web)
  /tips <hero>                 -> consejos para mejorar con un héroe específico (con búsqueda web)

No depende de ninguna API externa de Marvel Rivals para leer stats: Gemini lee
las capturas directamente (es multimodal). /meta y /tips sí usan la
herramienta de Google Search de Gemini, porque esa información cambia con
cada parche y no se puede confiar solo en el conocimiento estático del modelo.

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
import storage

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("marvel-rivals-bot")

DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

feedback_engine = FeedbackEngine()


async def _load_images(attachments: list[discord.Attachment]) -> list[tuple[bytes, str]]:
    """Descarga adjuntos de Discord y los deja listos para mandarlos a Gemini."""
    images = []
    for attachment in attachments:
        if not (attachment.content_type or "").startswith("image/"):
            raise ValueError(f"El archivo `{attachment.filename}` no parece ser una imagen.")
        data = await attachment.read()
        images.append((data, attachment.content_type))
    return images


# ---------- /link y /unlink ----------

@tree.command(name="link", description="Vincula tu cuenta de Discord con tu nombre de usuario de Marvel Rivals")
@app_commands.describe(usuario="Tu nombre de usuario exacto en Marvel Rivals")
async def link(interaction: discord.Interaction, usuario: str):
    storage.link_account(interaction.user.id, usuario.strip())
    await interaction.response.send_message(
        f"✅ Cuenta vinculada. A partir de ahora `/stats` usará **{usuario}** por defecto "
        "para saber en cuál jugador enfocarse.",
        ephemeral=True,
    )


@tree.command(name="unlink", description="Elimina la vinculación de tu cuenta de Marvel Rivals")
async def unlink(interaction: discord.Interaction):
    storage.unlink_account(interaction.user.id)
    await interaction.response.send_message("🗑️ Vinculación eliminada.", ephemeral=True)


# ---------- /stats: veredicto de tu desempeño en una partida ----------

@tree.command(name="stats", description="Analiza tu desempeño en una partida (KDA, final hits, curación, daño, etc.)")
@app_commands.describe(
    imagen="Captura del marcador final de la partida",
    usuario="Tu nombre de usuario en el juego (opcional si ya usaste /link)",
)
async def stats(interaction: discord.Interaction, imagen: discord.Attachment, usuario: str | None = None):
    await interaction.response.defer(thinking=True)

    player_name = usuario or storage.get_linked_account(interaction.user.id)
    if not player_name:
        await interaction.followup.send(
            "No tengo un usuario vinculado. Usa `/stats imagen:<captura> usuario:<tu_nombre>` "
            "o vincula tu cuenta primero con `/link`."
        )
        return

    try:
        images = await _load_images([imagen])
    except ValueError as e:
        await interaction.followup.send(f"⚠️ {e}")
        return

    try:
        verdict = feedback_engine.generate_match_verdict(player_name, images)
    except RuntimeError as e:
        await interaction.followup.send(f"⚠️ {e}")
        return
    except Exception:
        logger.exception("Error generando veredicto con Gemini")
        await interaction.followup.send("⚠️ Ocurrió un error generando el análisis con IA. Intenta de nuevo.")
        return

    embed = discord.Embed(
        title=f"📊 Veredicto de {player_name}",
        description=verdict,
        color=discord.Color.red(),
    )
    embed.set_footer(text="Análisis generado con Gemini")
    embed.set_thumbnail(url=imagen.url)
    await interaction.followup.send(embed=embed)


# ---------- /game: análisis imparcial de todos los jugadores ----------

@tree.command(name="game", description="Análisis imparcial de fortalezas/debilidades de todos los jugadores de la partida")
@app_commands.describe(imagen="Captura del marcador final de la partida")
async def game(interaction: discord.Interaction, imagen: discord.Attachment):
    await interaction.response.defer(thinking=True)

    try:
        images = await _load_images([imagen])
    except ValueError as e:
        await interaction.followup.send(f"⚠️ {e}")
        return

    try:
        overview = feedback_engine.generate_game_overview(images)
    except RuntimeError as e:
        await interaction.followup.send(f"⚠️ {e}")
        return
    except Exception:
        logger.exception("Error generando análisis de partida con Gemini")
        await interaction.followup.send("⚠️ Ocurrió un error generando el análisis con IA. Intenta de nuevo.")
        return

    embed = discord.Embed(
        title="🎮 Análisis imparcial de la partida",
        description=overview,
        color=discord.Color.blue(),
    )
    embed.set_footer(text="Análisis generado con Gemini")
    embed.set_thumbnail(url=imagen.url)
    await interaction.followup.send(embed=embed)


# ---------- /meta: meta actual de la temporada ----------

@tree.command(name="meta", description="Resumen del meta actual de Marvel Rivals (héroes fuertes de la temporada)")
async def meta(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)

    try:
        report = feedback_engine.generate_meta_report()
    except RuntimeError as e:
        await interaction.followup.send(f"⚠️ {e}")
        return
    except Exception:
        logger.exception("Error generando reporte de meta con Gemini")
        await interaction.followup.send("⚠️ Ocurrió un error consultando el meta actual. Intenta de nuevo.")
        return

    embed = discord.Embed(
        title="📈 Meta actual de Marvel Rivals",
        description=report,
        color=discord.Color.gold(),
    )
    embed.set_footer(text="Generado con Gemini + Google Search")
    await interaction.followup.send(embed=embed)


# ---------- /tips: consejos para un héroe específico ----------

@tree.command(name="tips", description="Consejos para mejorar jugando a un héroe específico")
@app_commands.describe(hero="Nombre del héroe (ej. Hela, Luna Snow, Doctor Strange)")
async def tips(interaction: discord.Interaction, hero: str):
    await interaction.response.defer(thinking=True)

    try:
        advice = feedback_engine.generate_hero_tips(hero.strip())
    except RuntimeError as e:
        await interaction.followup.send(f"⚠️ {e}")
        return
    except Exception:
        logger.exception("Error generando tips de héroe con Gemini")
        await interaction.followup.send("⚠️ Ocurrió un error generando los tips. Intenta de nuevo.")
        return

    embed = discord.Embed(
        title=f"💡 Tips para jugar {hero}",
        description=advice,
        color=discord.Color.purple(),
    )
    embed.set_footer(text="Generado con Gemini + Google Search")
    await interaction.followup.send(embed=embed)


@client.event
async def on_ready():
    await tree.sync()
    logger.info(f"Bot conectado como {client.user}")


if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise SystemExit("Falta DISCORD_BOT_TOKEN en tu archivo .env")
    client.run(DISCORD_TOKEN)