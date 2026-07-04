"""
Genera retroalimentación de desempeño usando la API de Gemini (Google),
a partir de stats de Marvel Rivals que el usuario pega como texto y/o
sube como captura(s) de pantalla.

SDK: google-genai (https://ai.google.dev/gemini-api/docs)
API key gratuita: https://aistudio.google.com/apikey

Gemini es multimodal: puede "leer" directamente una captura de pantalla del
menú de stats del juego sin necesidad de OCR ni de ninguna API externa de
Marvel Rivals. Eso es justo lo que aprovechamos aquí.
"""

import os
from google import genai
from google.genai import types

MODEL = "gemini-2.5-flash"

SYSTEM_PROMPT = """\
Eres un analista/coach de esports especializado en Marvel Rivals (shooter de héroes tipo Overwatch).
El usuario te va a compartir sus estadísticas de juego como texto pegado y/o como una o más
capturas de pantalla del menú de stats o historial de partidas del juego.

Tu tarea:
1. Primero, léelo con cuidado: identifica qué datos reales tienes disponibles (rango, KDA,
   héroes jugados, daño, healing, winrate, resultados de partidas, etc.). Si una imagen está
   borrosa o le falta información, dilo explícitamente en vez de inventar cifras.
2. Da un resumen breve y honesto del desempeño.
3. Señala 2-3 fortalezas concretas basadas en los números reales que sí puedes leer.
4. Señala 2-3 áreas de mejora concretas y accionables.
5. Si hay datos de varios héroes o varias partidas, compara y di dónde rinde mejor/peor y por qué.
6. Termina con 1-2 recomendaciones prácticas para la próxima sesión de juego.

Reglas de estilo:
- Responde en español, tono cercano pero profesional, como un coach que quiere que mejores.
- Usa SOLO los números que puedas leer del texto/imagen. Nunca inventes cifras.
- Si no hay suficiente información para alguna sección, dilo brevemente en vez de rellenar con genéricos.
- Sé conciso: máximo ~300 palabras.
"""


class FeedbackEngine:
    def __init__(self, api_key: str | None = None):
        self.client = genai.Client(api_key=api_key or os.getenv("GEMINI_API_KEY"))

    def generate(
        self,
        instruction: str,
        text: str | None = None,
        images: list[tuple[bytes, str]] | None = None,
    ) -> str:
        """
        instruction: qué queremos que analice (ej. "stats generales" o "últimas partidas").
        text: texto pegado por el usuario con sus stats (opcional).
        images: lista de (bytes_de_la_imagen, mime_type) con capturas de pantalla (opcional).
        """
        parts: list = [instruction]

        if text:
            parts.append(f"Texto de stats pegado por el usuario:\n{text}")

        for image_bytes, mime_type in images or []:
            parts.append(types.Part.from_bytes(data=image_bytes, mime_type=mime_type))

        if not text and not images:
            return "No recibí ni texto ni una imagen con stats para analizar."

        response = self.client.models.generate_content(
            model=MODEL,
            contents=parts,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=900,
            ),
        )

        return response.text
