# Marvel Rivals Coach Bot 🕸️📊

Bot de Discord que analiza tu desempeño en Marvel Rivals usando IA (Gemini).
Le subes una captura de pantalla del marcador final de una partida y te da
retroalimentación honesta y específica — sin depender de ninguna API externa
de Marvel Rivals (esas APIs no oficiales se han caído repetidamente).

## Comandos

| Comando | Qué hace |
|---|---|
| `/link usuario:<nombre>` | Vincula tu Discord con tu nombre de usuario del juego |
| `/unlink` | Borra la vinculación guardada |
| `/stats imagen:<captura> [usuario]` | Veredicto de **tu** desempeño en una partida: KDA, final hits, curación, daño, daño bloqueado |
| `/game imagen:<captura>` | Análisis **imparcial** de fortalezas/debilidades de **todos** los jugadores de la partida |
| `/meta` | Resumen del meta actual de la temporada vigente (héroes fuertes, nerfeados, etc.) |
| `/tips hero:<nombre>` | Consejos para mejorar jugando a un héroe específico |

### Sobre `/stats` vs `/game`
- **`/stats`** se enfoca solo en ti: busca tu fila en el marcador (usando el
  nombre que vinculaste con `/link`, o el que le pases con `usuario:`) y te
  da un veredicto sobre tu propio desempeño.
- **`/game`** ignora quién eres tú: analiza a todos los jugadores del
  marcador por igual, de forma imparcial — útil para entender qué decidió
  la partida en general, no solo tu actuación.

### Sobre `/meta` y `/tips`
Estos dos comandos usan la herramienta de **búsqueda de Google integrada en
Gemini** (no una API de Marvel Rivals) para asegurarse de dar información
actual, ya que el meta y el balance de héroes cambian con cada parche y el
conocimiento "de memoria" del modelo se queda desactualizado rápido.

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

Y los comandos aparecerán en tu servidor de Discord (puede tardar hasta una
hora en propagarse la primera vez; si no aparecen, reinicia Discord).

## 3. Cómo usarlo

1. `/link usuario:TuNombreExacto` (una sola vez).
2. Termina una partida en Marvel Rivals y toma captura del marcador final
   (el que muestra a todos los jugadores de ambos equipos).
3. `/stats imagen:<esa captura>` → tu veredicto personal.
4. O `/game imagen:<esa captura>` → análisis de toda la partida.
5. `/meta` en cualquier momento para ver qué está fuerte ahora.
6. `/tips hero:Hela` (o el héroe que quieras) para consejos específicos.

**Tip para que reconozca bien a los héroes:** si puedes, toma la captura
donde el nombre del héroe aparezca como **texto** en pantalla, no solo el
ícono/arte — es mucho más confiable que el ícono solo, sobre todo con
personajes nuevos.

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

> ⚠️ **Sobre `/link` y persistencia:** este bot guarda las vinculaciones en
> un archivo JSON local (`data/linked_accounts.json`). En Railway/Fly.io el
> sistema de archivos suele ser **efímero** — si no agregas un volumen
> persistente, ese archivo se puede borrar en cada redeploy y la gente
> tendría que volver a hacer `/link`. Para un bot personal esto no es grave;
> si te importa, agrega un volumen persistente y monta la carpeta `data/` ahí.

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
├── bot.py            # Bot de Discord y los 6 comandos slash
├── feedback.py        # Los 4 tipos de análisis con Gemini (2 multimodales + 2 con búsqueda web)
├── storage.py          # Vincula discord_id <-> usuario de Marvel Rivals (JSON local)
├── data/
│   └── linked_accounts.json   # se crea solo, no lo edites a mano
├── requirements.txt
├── .env.example
└── README.md
```

## 6. Por qué este diseño

Marvel Rivals (NetEase) no tiene una API pública oficial. Todo lo que existe
son proyectos de la comunidad que hacen scraping o ingeniería inversa del
juego, y en la práctica resultan frágiles — probamos dos y ambas terminaron
caídas o muertas en la misma semana. Por eso:
- **Stats de partidas** (`/stats`, `/game`): se leen directo de tu captura
  de pantalla con Gemini multimodal. Nada que se pueda caer del lado de un
  tercero no oficial.
- **Info que cambia con el tiempo** (`/meta`, `/tips`): se resuelve con
  búsqueda web en tiempo real (herramienta oficial de Google/Gemini), no con
  una API de un tercero ni con el conocimiento fijo del modelo.

## 7. Próximos pasos posibles

- Guardar tus veredictos anteriores para comparar tu progreso a lo largo del tiempo.
- Permitir subir varias capturas a `/stats`/`/game` para analizar una racha completa.
- Cachear `/meta` por algunas horas para no gastar una búsqueda por cada persona que lo pida.
