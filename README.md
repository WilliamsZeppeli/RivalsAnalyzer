# Marvel Rivals Coach Bot 🕸️📊

Bot de Discord que analiza tu desempeño en Marvel Rivals usando IA (Gemini).
Le pegas texto con tus stats y/o le subes una captura de pantalla del juego,
y te da retroalimentación honesta y específica.

**No depende de ninguna API externa de Marvel Rivals.** Las dos APIs
comunitarias que probamos antes (marvelrivalsapi.com y mrapi.org) dejaron de
funcionar en la misma semana — son proyectos no oficiales mantenidos por
voluntarios, y pueden caerse sin aviso. Para evitar ese punto de falla,
este bot usa a Gemini directamente como "lector" multimodal: le mandas una
captura de pantalla de tu menú de stats o de tu historial de partidas, y el
modelo la interpreta él mismo, sin pasar por ningún tercero.

## Comandos

| Comando | Qué hace |
|---|---|
| `/analizar [texto] [imagen]` | Analiza tus stats generales (rango, héroes, KDA, etc.) |
| `/partidas [texto] [imagen1] [imagen2] [imagen3]` | Analiza tus últimas partidas |

En ambos comandos puedes:
- Pegar el texto de tus stats (cópialo tal cual del juego o de donde lo tengas), y/o
- Subir una o varias capturas de pantalla (el menú de stats del juego, o el resumen
  de la partida al terminarla).

No hace falta usar los dos a la vez — con solo la imagen ya funciona.

## 1. Requisitos previos

Solo necesitas 2 credenciales:

### a) Token del bot de Discord
1. Ve a https://discord.com/developers/applications → **New Application**.
2. En la pestaña **Bot**, crea el bot y copia el **Token**.
3. En **OAuth2 → URL Generator**, marca los scopes `bot` y `applications.commands`,
   y en permisos marca al menos `Send Messages` y `Use Slash Commands`. Usa la URL
   generada para invitar el bot a tu servidor.

### b) API key de Gemini
1. Entra a https://aistudio.google.com/apikey con tu cuenta de Google.
2. Haz clic en **Create API Key** y cópiala.

## 2. Instalación local

```bash
git clone <este-proyecto>  # o simplemente copia la carpeta
cd marvel-rivals-bot

python -m venv venv
source venv/bin/activate      # en Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# abre .env y pega tus 2 credenciales
```

Ejecutar el bot:

```bash
python bot.py
```

Si todo está bien configurado, verás en la consola:
```
Bot conectado como TuBot#1234
```

Y los comandos `/analizar` y `/partidas` aparecerán en tu servidor de Discord
(puede tardar hasta una hora en propagarse la primera vez; si no aparecen,
reinicia Discord).

## 3. Cómo usarlo

1. Abre Marvel Rivals y ve a tu menú de stats (career/perfil) o al resumen
   de una partida que acabes de jugar.
2. Toma una captura de pantalla.
3. En Discord: `/analizar` y adjunta la imagen en el parámetro `imagen`
   (o pega el texto si ya tienes tus stats copiadas en algún lado).
4. Para varias partidas seguidas, usa `/partidas` y puedes subir hasta 3
   capturas a la vez.

## 4. Desplegarlo 24/7 (para que no dependa de tu compu)

Recomendación: **Railway** (más simple para empezar) o **Fly.io** (más control,
capa gratuita más generosa). Ambos soportan procesos de Python de larga duración.

### Opción A: Railway
1. Sube esta carpeta a un repo de GitHub.
2. En https://railway.app/ → **New Project** → **Deploy from GitHub repo**.
3. En **Variables**, agrega `DISCORD_BOT_TOKEN` y `GEMINI_API_KEY`
   (los mismos valores de tu `.env`).
4. En **Settings → Start Command**, pon `python bot.py`.
5. Railway detecta `requirements.txt` automáticamente e instala todo.

### Opción B: Fly.io
1. Instala el CLI: https://fly.io/docs/hands-on/install-flyctl/
2. Dentro de la carpeta del proyecto: `fly launch` (dile que no necesitas
   base de datos ni servicio web público — este bot no expone puertos).
3. Configura los secretos:
   ```bash
   fly secrets set DISCORD_BOT_TOKEN=xxx GEMINI_API_KEY=xxx
   ```
4. `fly deploy`

En ambos casos, cuida que el `Procfile`/start command corra `python bot.py` como
un **worker**, no como servicio web (el bot no necesita recibir peticiones HTTP).

## 5. Estructura del proyecto

```
marvel-rivals-bot/
├── bot.py            # Bot de Discord y comandos slash
├── feedback.py        # Llama a Gemini (texto + imágenes) para generar el análisis
├── requirements.txt
├── .env.example
└── README.md
```

## 6. Por qué este diseño y no una API de stats

Marvel Rivals (NetEase) no tiene una API pública oficial. Todo lo que existe
son proyectos de la comunidad que hacen scraping o ingenieria inversa del
juego, y en la práctica resultan frágiles: pueden quedar caídos días o
semanas, cambiar de formato sin aviso, o desaparecer. Si en el futuro quieres
agregar de todas formas una fuente de datos automática (en vez de pegar
captura/texto a mano), lo más simple es escribir un cliente HTTP nuevo (como
los que probamos antes) y conectarlo como una fuente opcional adicional —
pero el núcleo del bot (leer stats con Gemini) seguiría funcionando aunque
esa fuente externa se caiga.

## 7. Próximos pasos posibles

- Guardar tus análisis anteriores (con `window.storage` si lo llevas a un
  artifact, o una base de datos si crece el bot) para comparar tu progreso.
- Permitir subir más de 3 imágenes por comando si quieres analizar una racha completa.
- Agregar un modo "comparar dos capturas" (antes/después) para ver tu evolución.
