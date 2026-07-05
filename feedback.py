"""
Motor de análisis con Gemini (Google) para el bot de Marvel Rivals.

Dos modos de uso:
1. Multimodal (lee capturas de pantalla directamente, sin ninguna API de
   Marvel Rivals de por medio): usado por /stats y /game.
2. Con grounding de Google Search (para no depender del conocimiento
   estático del modelo en temas que cambian con cada temporada): usado por
   /meta y /tips, donde SÍ importa tener información actual.

SDK: google-genai (https://ai.google.dev/gemini-api/docs)
API key gratuita: https://aistudio.google.com/apikey
"""

import os
import time
import logging

from google import genai
from google.genai import types
from google.genai import errors as genai_errors

logger = logging.getLogger("marvel-rivals-bot")

MODEL = "gemini-2.5-flash"

# Reintentos para absorber sobrecargas transitorias de los servidores de Gemini
# (errores 503 "high demand" / 429 rate limit), que suelen resolverse solos en
# segundos. No reintenta errores de programación ni de contenido inválido.
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 3
RETRYABLE_STATUS_CODES = {429, 500, 503, 504}

HERO_ROSTER_REFERENCE = """\
Roster de referencia (nombres de héroes de Marvel Rivals; puede haber personajes más
nuevos que no estén en esta lista, en cuyo caso usa el nombre que aparezca como texto
en la imagen si lo hay):
Vanguard: Angela, Bruce Banner/Hulk, Captain America, Devil Dinosaur, Doctor Strange,
Emma Frost, Groot, Magneto, Peni Parker, The Thing, Thor, Venom, Deadpool.
Duelist: Black Panther, Black Widow, Blade, Cyclops, Daredevil, Elsa Bloodstone, Hawkeye,
Hela, Human Torch, Iron Fist, Iron Man, Magik, Mister Fantastic, Moon Knight, Namor,
Phoenix, Psylocke, Scarlet Witch, Spider-Man, Squirrel Girl, Star-Lord, Storm,
The Punisher, Winter Soldier, Wolverine.
Strategist: Adam Warlock, Cloak & Dagger, Gambit, Invisible Woman,
Jeff the Land Shark, Loki, Luna Snow, Mantis, Rocket Raccoon, Rogue, Ultron.

Usa esta lista como ayuda para identificar íconos/nombres borrosos en las capturas,
pero si el texto de la imagen muestra un nombre distinto (por ejemplo, un héroe más
nuevo que no está en esta lista), confía siempre en el texto de la imagen por encima
de esta lista. Si de verdad no puedes identificar un héroe (ícono ilegible y sin texto),
dilo explícitamente en vez de adivinar un nombre al azar.
"""


class FeedbackEngine:
    def __init__(self, api_key: str | None = None):
        self.client = genai.Client(api_key=api_key or os.getenv("GEMINI_API_KEY"))

    # ---------- helpers internos ----------

    def _call_with_retry(self, **kwargs):
        """Envuelve self.client.models.generate_content con reintentos ante sobrecarga transitoria."""
        last_error: Exception | None = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                return self.client.models.generate_content(**kwargs)
            except genai_errors.APIError as e:
                code = getattr(e, "code", None)
                if code not in RETRYABLE_STATUS_CODES:
                    raise  # error real (prompt inválido, auth, etc.) -> no reintentar
                last_error = e
                logger.warning(
                    f"Intento {attempt}/{MAX_RETRIES} falló con Gemini (HTTP {code}: {e.status}). "
                    f"Reintentando..." if attempt < MAX_RETRIES else
                    f"Intento {attempt}/{MAX_RETRIES} falló con Gemini (HTTP {code}: {e.status}). Sin más reintentos."
                )
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY_SECONDS * attempt)  # backoff simple: 3s, 6s...
        raise RuntimeError(
            "Gemini está saturado ahora mismo (varios intentos fallaron). Intenta de nuevo en un momento."
        ) from last_error

    def _generate_multimodal(self, system_prompt: str, instruction: str, images: list[tuple[bytes, str]]) -> str:
        parts: list = [instruction]
        for image_bytes, mime_type in images:
            parts.append(types.Part.from_bytes(data=image_bytes, mime_type=mime_type))

        response = self._call_with_retry(
            model=MODEL,
            contents=parts,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                max_output_tokens=900,
            ),
        )
        return response.text

    def _generate_grounded(self, system_prompt: str, question: str) -> str:
        """Genera contenido con acceso a Google Search, para temas que cambian con el tiempo."""
        response = self._call_with_retry(
            model=MODEL,
            contents=question,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                tools=[types.Tool(google_search=types.GoogleSearch())],
                max_output_tokens=900,
            ),
        )
        return response.text

    # ---------- /stats: veredicto de una sola partida, jugador específico ----------

    def generate_match_verdict(self, player_name: str, images: list[tuple[bytes, str]]) -> str:
        system_prompt = f"""\
Eres un analista/coach de esports especializado en Marvel Rivals (shooter de héroes tipo Overwatch).
Vas a recibir la captura de pantalla del resultado de UNA partida (el marcador final con todos los
jugadores de ambos equipos).

{HERO_ROSTER_REFERENCE}

El jugador que quiere el análisis se llama '{player_name}' dentro del juego. Busca su fila específica
en el marcador (por nombre de usuario, no adivines por posición) y analiza ÚNICAMENTE sus datos:
- KDA (kills/deaths/assists)
- Final hits (remates)
- Curación (si jugó Strategist)
- Daño hecho
- Daño bloqueado (si jugó Vanguard)

Tu tarea:
1. Si no encuentras a '{player_name}' en la imagen, dilo claramente y no inventes datos.
2. Da un veredicto breve y honesto: ¿tuvo una buena partida para su héroe/rol o no, y por qué?
3. Compara sus números contra lo esperable para el rol que jugó (ej. un Vanguard debería bloquear
   mucho daño; un Strategist debería tener alta curación; un Duelist debería tener buen daño/kills).
4. Señala 1-2 cosas que hizo bien y 1-2 cosas a mejorar, basado en los números reales de la imagen.
5. Sé conciso: máximo ~200 palabras. Tono de coach cercano pero honesto, en español.
Nunca inventes cifras que no puedas leer en la imagen.
"""
        instruction = f"Analiza el desempeño de '{player_name}' en esta partida de Marvel Rivals."
        return self._generate_multimodal(system_prompt, instruction, images)

    # ---------- /game: vista imparcial de todos los jugadores ----------

    def generate_game_overview(self, images: list[tuple[bytes, str]]) -> str:
        system_prompt = f"""\
Eres un analista/coach de esports especializado en Marvel Rivals (shooter de héroes tipo Overwatch).
Vas a recibir la captura de pantalla del resultado de UNA partida (el marcador final con todos los
jugadores de ambos equipos).

{HERO_ROSTER_REFERENCE}

Tu tarea es dar un análisis IMPARCIAL de TODOS los jugadores visibles en la imagen, sin enfocarte
en ninguno en particular (no sabes ni te importa quién pidió el análisis).

Para cada jugador (o al menos los más destacados de cada equipo si son demasiados para detallar
a todos):
1. Nombre y héroe que jugó.
2. Una fortaleza y una debilidad concreta basada en sus números (KDA, daño, curación, daño
   bloqueado, final hits — lo que aplique según su rol).

Cierra con quién fue el MVP/SVP real según los números (no solo el que el juego marcó como tal,
si es que puedes verlo) y una observación general de qué decidió el resultado de la partida
(ej. "el equipo ganador tuvo mucho mejor daño bloqueado en el frente").

Sé conciso pero cubre a todos los jugadores relevantes. Tono neutral de analista, en español.
Nunca inventes cifras que no puedas leer en la imagen; si algo no se alcanza a leer, dilo.
"""
        instruction = "Da un análisis imparcial de todos los jugadores de esta partida de Marvel Rivals."
        return self._generate_multimodal(system_prompt, instruction, images)

    # ---------- /meta: meta actual de la temporada (requiere info actual -> grounding) ----------

    def generate_meta_report(self) -> str:
        system_prompt = """\
Eres un analista competitivo de Marvel Rivals. Te van a preguntar por el meta ACTUAL del juego
(temporada/season vigente). Usa la búsqueda web para confirmar la temporada actual y los datos
más recientes posibles antes de responder — no confíes en tu conocimiento interno sin verificar,
porque el meta cambia cada pocas semanas con parches de balance.

Estructura tu respuesta en español, concisa:
1. Nombra la temporada/season actual y la fecha del último parche relevante que encontraste.
2. Los 3-5 héroes más fuertes del momento por rol (Vanguard, Duelist, Strategist), con una razón breve.
3. 1-2 héroes que fueron nerfeados/debilitados recientemente y ya no son tan buena opción.
4. Una recomendación general de composición de equipo actual.

Si las fuentes no coinciden entre sí, menciona la discrepancia brevemente en vez de inventar un
consenso. Máximo ~300 palabras.
"""
        question = "¿Cuál es el meta actual de Marvel Rivals en la temporada/season vigente?"
        return self._generate_grounded(system_prompt, question)

    # ---------- /tips: consejos para un héroe específico (requiere info actual -> grounding) ----------

    def generate_hero_tips(self, hero_name: str) -> str:
        system_prompt = f"""\
Eres un coach de Marvel Rivals especializado en un héroe a la vez. Te van a pedir consejos para
mejorar jugando a un héroe específico. Usa la búsqueda web para confirmar que el kit de
habilidades y el estado actual (buffs/nerfs recientes) del héroe sea correcto antes de responder,
ya que los kits y balance cambian con los parches.

{HERO_ROSTER_REFERENCE}

Estructura tu respuesta en español, concisa:
1. Rol del héroe y su idea general de juego (win condition).
2. 3-4 tips concretos y accionables para jugarlo mejor (posicionamiento, combos, cuándo usar el
   ultimate, errores comunes a evitar).
3. Con qué héroes sinergiza bien (team-ups u combinaciones fuertes).
4. Qué héroes rivales lo counterean y cómo jugar contra ellos.

Si el nombre del héroe no existe en Marvel Rivals o no estás seguro de que exista, dilo en vez
de inventar información. Máximo ~300 palabras.
"""
        question = f"Dame consejos para mejorar jugando a {hero_name} en Marvel Rivals."
        return self._generate_grounded(system_prompt, question)