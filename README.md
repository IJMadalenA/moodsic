# MoodSic

MoodSic es un sistema de recomendación musical contextual que genera playlists personalizadas usando historial del usuario, contexto externo y aprendizaje por refuerzo.

El proyecto está preparado para funcionar en dos modos:

- modo online, usando Spotify y servicios externos como contexto;
- modo offline, usando datos sintéticos y benchmarks reproducibles para desarrollo, pruebas y demos.

## Qué hace el proyecto

- genera playlists personalizadas para cada usuario;
- registra feedback de escucha y calcula reward;
- incorpora clima, noticias y momento del día en el estado del recomendador;
- permite entrenamiento y evaluación del agente RL;
- ofrece utilidades de benchmarking para comparar configuraciones de forma reproducible.

## Stack principal

- Django y Django Ninja para backend y API;
- Spotify vía Spotipy para catálogo y sincronización opcional;
- Open-Meteo y NewsAPI como contexto externo;
- TensorFlow/Keras para el agente de aprendizaje por refuerzo;
- SQLite por defecto en local, con soporte de contenedor para otros entornos.

## Estructura del proyecto

### Aplicaciones Django

- apps/users: autenticación y conexión con Spotify.
- apps/music: catálogo de tracks, artistas, álbumes y sincronización musical.
- apps/context: datos de clima y noticias.
- apps/interactions: generación de playlists, feedback, reward y API principal.
- apps/dashboard: métricas agregadas para panel de control.

### Capa de IA

- ml/agent.py: agente DQN.
- ml/state_builder.py: construcción del vector de estado.
- ml/reward.py: cálculo matemático del reward.
- ml/training.py: entrenamiento, evaluación y persistencia del modelo.

### Pipelines y utilidades

- pipelines/: ETL de contexto y preparación de estado.
- apps/interactions/management/commands/: comandos de entrenamiento, benchmarking, sincronización y utilidades operativas.

## Puesta en marcha rápida

### 1. Entorno

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configuración

```bash
copy .env.example .env
```

Rellena lo necesario en el archivo .env. Para desarrollo local sin APIs reales, el proyecto puede funcionar igualmente con datos sintéticos.

### 3. Base de datos y servidor

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### 4. Puntos de entrada útiles

- Admin: /admin/
- API base: /api/interactions/
- Swagger/OpenAPI: /api/interactions/docs/

## Flujo recomendado para desarrollo offline

```bash
python manage.py seed_synthetic_context
python manage.py seed_synthetic_interactions
python manage.py train_agent --with-synthetic-context --episodes 5
python manage.py evaluate_model --with-synthetic-context --auto-train
python manage.py benchmark_matrix --config ml/benchmark_matrix_config.example.json
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
- comandos operativos: MANAGEMENT_COMMANDS.md
- plan técnico de integración: docs/INTEGRATION_PLAN_DEV.md
