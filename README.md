# MoodSic

MoodSic es un sistema de recomendación musical contextual que genera playlists personalizadas usando historial del usuario, contexto externo y aprendizaje por refuerzo.

El proyecto funciona en dos modos:

- **modo online**: autenticación real con Spotify OAuth, análisis de hasta 500 canciones del historial del usuario y generación de playlists vía agente RL con clima real de la ciudad del usuario;
- **modo offline**: datos sintéticos y benchmarks reproducibles para desarrollo, pruebas y demos sin depender de APIs externas.

## Qué hace el proyecto

- analiza hasta 500 canciones del historial de Spotify del usuario (liked tracks, top tracks, recently played);
- genera playlists personalizadas de N canciones usando un agente DQN entrenado;
- incorpora clima real (Open-Meteo), noticias (NewsAPI) y momento del día en el estado del recomendador;
- permite al usuario configurar su ciudad desde el perfil web para obtener clima de su ubicación real;
- registra feedback de escucha y calcula reward para seguir entrenando el modelo;
- sincroniza las playlists generadas directamente a la cuenta de Spotify del usuario;
- ofrece utilidades de benchmarking para comparar configuraciones de forma reproducible.

## Stack principal

- Python 3.13, Django 4.2, Django Ninja 1.6 para backend y API REST;
- PostgreSQL (Docker) como base de datos principal, Redis (Docker) para caché y tareas;
- Spotify OAuth via django-allauth + Spotipy para autenticación y sincronización;
- Open-Meteo (gratuito, sin API key) para datos climáticos por coordenadas;
- NewsAPI para contexto de noticias;
- django-cities-light para base de datos geográfica local (países y ciudades);
- TensorFlow 2.21 / Keras para el agente DQN de aprendizaje por refuerzo.

## Estructura del proyecto

### Aplicaciones Django

- **apps/users**: autenticación, perfiles de usuario, conexión OAuth con Spotify y selector de ciudad.
- **apps/music**: catálogo local de tracks, artistas y álbumes; sincronización con Spotify.
- **apps/context**: datos de clima (WeatherContext) y noticias (NewsContext) con actualización periódica.
- **apps/interactions**: núcleo del sistema — generación de playlists, feedback, reward y API principal.
- **apps/dashboard**: métricas agregadas para panel de control.

### Capa de IA (`ml/`)

- `agent.py`: agente DQN con target network y experience replay. Arquitectura: Input(45) → Dense(128) → Dense(128) → Dense(64) → Output(100).
- `state_builder.py`: construye el vector de estado de 45 dimensiones (clima ×10, audio ×12, historial ×8, contexto ×15).
- `reward.py`: cálculo del reward multifactor en rango [-2.0, 3.0+].
- `training.py`: entrenamiento, evaluación y persistencia del modelo.
- `models/`: modelos entrenados (`.h5`). Modelo activo: `dqn_agent_20260430_163358.h5`.

### Pipelines y comandos de gestión

- `pipelines/`: ETL de contexto y preparación de estado.
- `apps/interactions/management/commands/`: `analyze_and_generate`, `train_agent`, `evaluate_model`, `benchmark_matrix` y más.
- `apps/context/management/commands/`: `refresh_context` para actualizar clima y noticias.

## Puesta en marcha

### 1. Requisitos previos

- Docker Desktop instalado y en ejecución.
- Python 3.13 con `uv` o `pip`.
- Credenciales de Spotify Developer (Client ID + Secret) con redirect URI configurada.
- API key de NewsAPI (gratuita en newsapi.org).

### 2. Entorno

```bash
uv venv
uv sync
```

### 3. Configuración

```bash
copy .env.example .env
```

Variables obligatorias en `.env`:

```
DATABASE_URL=postgres://cmoodsic_db_user:cmoodsic_db_pass@localhost:5434/cmoodsic_db
SPOTIPY_CLIENT_ID=<tu_client_id>
SPOTIPY_CLIENT_SECRET=<tu_client_secret>
SPOTIPY_REDIRECT_URI=http://127.0.0.1:8000/accounts/spotify/login/callback/
NEWSAPI_KEY=<tu_newsapi_key>
SECRET_KEY=<django_secret_key>
DEBUG=True
```

### 4. Infraestructura Docker

```bash
docker-compose up -d
```

Levanta PostgreSQL en el puerto 5434 y Redis en el 6379.

### 5. Base de datos

```bash
uv run manage.py migrate
uv run manage.py createsuperuser

# Importar datos geográficos de España (necesario para el selector de ciudad)
uv run manage.py cities_light
```

### 6. Servidor

```bash
uv run manage.py runserver
```

### 7. Puntos de entrada

| URL | Descripción |
|-----|-------------|
| `/` | Página principal |
| `/admin/` | Panel de administración Django |
| `/accounts/profile/` | Perfil de usuario (selector de ciudad incluido) |
| `/dashboard/` | Panel de métricas |
| `/api/interactions/docs/` | Swagger / OpenAPI |

## Uso principal: generar una playlist

Una vez autenticado con Spotify:

```bash
uv run manage.py analyze_and_generate --username <email> --max-tracks 500 --count 35
```

Esto:
1. Recopila hasta 500 canciones del historial de Spotify del usuario.
2. Las persiste en la base de datos local.
3. Obtiene el clima real de la ciudad del usuario desde Open-Meteo.
4. Ejecuta el agente RL para seleccionar 35 canciones.
5. Crea la playlist en Spotify y muestra el enlace directo.

## Flujo recomendado para desarrollo offline

```bash
uv run manage.py seed_synthetic_context
uv run manage.py seed_synthetic_interactions
uv run manage.py train_agent --with-synthetic-context --episodes 5
uv run manage.py evaluate_model --with-synthetic-context --auto-train
uv run manage.py benchmark_matrix --config ml/benchmark_matrix_config.example.json
```

## Qué leer primero si eres nuevo en el proyecto

1. docs/ONBOARDING.md
2. MANAGEMENT_COMMANDS.md
3. DEVELOPMENT.md
4. apps/interactions/services/playlist_generation_service.py
5. ml/state_builder.py y ml/reward.py

## Estado actual del proyecto

Actualmente MoodSic dispone de:

- flujo híbrido online/offline para generar playlists;
- soporte de contexto meteorológico y de noticias;
- entrenamiento y evaluación del recomendador;
- benchmarking reproducible con ranking, robustez y sensibilidad por alpha;
- tests automatizados sobre API, reward, contexto y scoring de playlists.

## Documentación adicional

- índice general: docs/README.md
- guía de onboarding: docs/ONBOARDING.md
- nota de cambios finales: docs/FINAL_CHANGES_2026-04-15.md
- checklist de entrega y defensa: docs/DELIVERY_CHECKLIST.md
- comandos operativos: MANAGEMENT_COMMANDS.md
- plan técnico de integración: docs/INTEGRATION_PLAN_DEV.md
