# Marvel Rivals Coach Bot 🕸️📊

Bot de Discord que trae tus estadísticas de Marvel Rivals y te da retroalimentación
de tu desempeño usando IA (Gemini).

## Comandos

| Comando | Qué hace |
|---|---|
| `/link usuario:<TuNombre#1234>` | Vincula tu Discord con tu cuenta de Marvel Rivals |
| `/stats [usuario]` | Stats generales + análisis de IA |
| `/partidas [usuario] [cantidad]` | Analiza tus últimas N partidas (por defecto 10) |
| `/unlink` | Borra la vinculación guardada |

## 1. Requisitos previos

Necesitas 3 credenciales antes de arrancar:

### a) Token del bot de Discord
1. Ve a https://discord.com/developers/applications → **New Application**.
2. En la pestaña **Bot**, crea el bot y copia el **Token**.
3. En **OAuth2 → URL Generator**, marca los scopes `bot` y `applications.commands`,
   y en permisos marca al menos `Send Messages` y `Use Slash Commands`. Usa la URL
   generada para invitar el bot a tu servidor.

### b) API key de Marvel Rivals
1. Entra a https://marvelrivalsapi.com/ y crea una cuenta.
2. Genera tu API key desde el dashboard (plan gratuito: 3,000 requests/día,
   suficiente para uso personal o de un servidor chico).

### c) API key de Gemini
1. Entra a https://aistudio.google.com/apikey con tu cuenta de Google.
2. Haz clic en **Create API Key** y cópiala.

> ⚠️ La API de MarvelRivalsAPI.com es una API **no oficial** hecha por la comunidad.
> Los nombres exactos de los campos en las respuestas pueden cambiar con el tiempo.
> Si algún comando empieza a fallar o a dar respuestas raras, revisa
> `stats_utils.py` — ahí es donde se interpretan los campos del JSON, y basta
> con imprimir la respuesta cruda (`print(json.dumps(raw, indent=2))`) para
> ver qué cambió y ajustar las llaves.

## 2. Instalación local

```bash
git clone <este-proyecto>  # o simplemente copia la carpeta
cd marvel-rivals-bot

python -m venv venv
source venv/bin/activate      # en Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# abre .env y pega tus 3 credenciales
```

Ejecutar el bot:

```bash
python bot.py
```

Si todo está bien configurado, verás en la consola:
```
Bot conectado como TuBot#1234
```

Y los comandos `/link`, `/stats`, `/partidas`, `/unlink` aparecerán en tu servidor
de Discord (puede tardar hasta una hora en propagarse la primera vez; si no
aparecen, reinicia Discord).

## 3. Desplegarlo 24/7 (para que no dependa de tu compu)

Recomendación: **Railway** (más simple para empezar) o **Fly.io** (más control,
capa gratuita más generosa). Ambos soportan procesos de Python de larga duración.

### Opción A: Railway
1. Sube esta carpeta a un repo de GitHub.
2. En https://railway.app/ → **New Project** → **Deploy from GitHub repo**.
3. En **Variables**, agrega `DISCORD_BOT_TOKEN`, `MARVEL_RIVALS_API_KEY`,
   `GEMINI_API_KEY` (los mismos valores de tu `.env`).
4. En **Settings → Start Command**, pon `python bot.py`.
5. Railway detecta `requirements.txt` automáticamente e instala todo.

### Opción B: Fly.io
1. Instala el CLI: https://fly.io/docs/hands-on/install-flyctl/
2. Dentro de la carpeta del proyecto: `fly launch` (dile que no necesitas
   base de datos ni servicio web público — este bot no expone puertos).
3. Configura los secretos:
   ```bash
   fly secrets set DISCORD_BOT_TOKEN=xxx MARVEL_RIVALS_API_KEY=xxx GEMINI_API_KEY=xxx
   ```
4. `fly deploy`

En ambos casos, cuida que el `Procfile`/start command corra `python bot.py` como
un **worker**, no como servicio web (el bot no necesita recibir peticiones HTTP).

## 4. Estructura del proyecto

```
marvel-rivals-bot/
├── bot.py            # Bot de Discord y comandos slash
├── marvel_api.py      # Cliente HTTP para MarvelRivalsAPI.com
├── feedback.py        # Llama a Gemini para generar el análisis
├── stats_utils.py      # Recorta/normaliza el JSON antes de mandarlo a Gemini
├── storage.py          # Vincula discord_id <-> usuario de Marvel Rivals (JSON local)
├── data/
│   └── linked_accounts.json   # se crea solo, no lo edites a mano
├── requirements.txt
├── .env.example
└── README.md
```

## 5. Próximos pasos posibles

- Guardar el historial de análisis para mostrar progreso a lo largo del tiempo.
- Comparar tus stats contra el promedio del rango (la API tiene leaderboards).
- Agregar gráficas (ej. con `matplotlib`) de tu winrate por héroe.
- Cambiar `storage.py` por una base de datos real si el bot crece a muchos servidores.
