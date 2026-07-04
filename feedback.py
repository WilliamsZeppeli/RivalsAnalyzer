"""
Genera retroalimentación de desempeño usando la API de Gemini (Google),
a partir de las estadísticas obtenidas de Marvel Rivals.

SDK: google-genai (https://ai.google.dev/gemini-api/docs)
API key gratuita: https://aistudio.google.com/apikey
"""

import os
import json
from google import genai
from google.genai import types

MODEL = "gemini-2.5-flash"  # rápido y barato, suficiente para este análisis

SYSTEM_PROMPT = """\
Eres un analista/coach de esports especializado en Marvel Rivals (shooter de héroes tipo Overwatch).
Recibirás datos crudos en JSON con las estadísticas y/o historial de partidas de un jugador.

Tu tarea:
1. Da un resumen breve y honesto de su desempeño reciente.
2. Señala 2-3 fortalezas concretas basadas en los números (ej. buen healing, buena participación en kills, etc).
3. Señala 2-3 áreas de mejora concretas y accionables (ej. muere demasiado, poco daño para su rol, mal winrate con cierto héroe).
4. Si hay datos de varios héroes, di con cuáles rinde mejor y con cuáles peor, y por qué crees que pasa eso.
5. Termina con 1-2 recomendaciones prácticas para la próxima sesión de juego.

Reglas de estilo:
- Responde en español, tono cercano pero profesional, como un coach que quiere que mejores.
- Sé específico y usa los números reales que te dieron, no inventes cifras.
- No hagas suposiciones sobre datos que no están en el JSON.
- Sé conciso: máximo ~250 palabras.
"""


class FeedbackEngine:
    def __init__(self, api_key: str | None = None):
        self.client = genai.Client(api_key=api_key or os.getenv("GEMINI_API_KEY"))

    def generate(self, player_name: str, stats_payload: dict) -> str:
        """
        stats_payload: dict con las stats/match history relevantes ya recortadas
        (no mandes el JSON completo y gigante de la API, filtra antes lo importante).
        """
        user_message = (
            f"Jugador: {player_name}\n\n"
            f"Datos (JSON):\n{json.dumps(stats_payload, ensure_ascii=False, indent=2)}"
        )

        response = self.client.models.generate_content(
            model=MODEL,
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=700,
            ),
        )

        return response.text
