# Guía de onboarding de MoodSic

Esta guía está pensada para una persona que entra nueva al proyecto y necesita entender rápido qué hace MoodSic, cómo está organizado y por dónde empezar.

## 1. Resumen ejecutivo

MoodSic es una plataforma que genera playlists personalizadas combinando:

- historial real de Spotify del usuario (hasta 500 canciones);
- contexto externo — clima real de la ciudad del usuario (Open-Meteo) y noticias (NewsAPI);
- un recomendador basado en aprendizaje por refuerzo (DQN).

El sistema funciona en **modo online** (Spotify OAuth + APIs reales) y **modo offline** (datos sintéticos para desarrollo y benchmarking).

## 2. Objetivo funcional

La idea principal es que el sistema no recomiende música de forma genérica, sino contextual:

- el usuario configura su ciudad en el perfil → el sistema obtiene el clima real de esa ubicación;
- si el clima cambia, la selección puede adaptarse;
- el historial de escucha del usuario pesa en la decisión del agente RL;
- las playlists generadas se sincronizan directamente a Spotify.

## 3. Cómo se organiza el proyecto

### apps/users
Autenticación, perfiles y conexión OAuth con Spotify. Incluye el campo `city` (FK a `cities_light.City`) que el usuario puede configurar desde `/accounts/profile/` mediante un buscador con autocompletado AJAX. La ciudad determina de dónde se obtiene el clima.

Vistas clave:
- `profile_view` — muestra el perfil
- `update_profile` — guarda la ciudad seleccionada (POST)
- `search_cities` — endpoint AJAX `/accounts/profile/cities/?q=...` que devuelve ciudades filtradas en JSON

### apps/music
Catálogo local de tracks, artistas y álbumes. Sincronización con Spotify:
- `spotify_music_service.py`: liked tracks paginados, top tracks (3 rangos), recently played, playlists propias.
- `music_data_service.py`: persistencia en BD. `preview_url` acepta cadena vacía (Spotify puede devolver `null`).

### apps/context
Contexto externo:
- `WeatherContext`: temperatura, humedad, viento, nubes (`clouds_all`), lluvia (`rain_1h`), estado WMO. Se obtiene de Open-Meteo con las coordenadas de la ciudad del usuario.
- `NewsContext`: noticias desde NewsAPI.
- `refresh_context`: comando que actualiza clima para todas las ciudades de usuarios activos. Si ningún usuario tiene ciudad, usa Madrid y Barcelona como respaldo.

### apps/interactions
Núcleo funcional:
- Genera playlists usando el agente DQN.
- Registra interacciones del usuario y calcula reward.
- Expone la API REST principal.
- Comando `analyze_and_generate`: orquesta todo el flujo online.

### apps/dashboard
Métricas y vistas agregadas para seguimiento del sistema.

### ml
Lógica del modelo de recomendación:
- `agent.py`: DQN con target network, experience replay, epsilon-greedy.
- `state_builder.py`: vector de estado de 45 dimensiones. El bloque de clima (`_extract_weather_features`) lee los campos del `WeatherContext` pasado como dict.
- `reward.py`: reward multifactor [-2.0, 3.0+].
- `training.py`: entrenamiento y persistencia.
- Modelo activo: `ml/models/dqn_agent_20260430_163358.h5`

### pipelines
Utilidades de ETL y preparación de datos/contexto.

## 4. Flujo principal del sistema (modo online)

1. El usuario inicia sesión con Spotify OAuth (`/accounts/spotify/login/`).
2. Configura su ciudad en `/accounts/profile/` (buscador de ciudad con AJAX).
3. `analyze_and_generate` recopila hasta 500 canciones de su historial de Spotify.
4. Se persisten en BD local (`Track`).
5. Se obtiene el clima real de su ciudad (Open-Meteo) y se guarda como `WeatherContext`.
6. Se construye el estado de 45 dimensiones para el agente DQN.
7. El agente selecciona N canciones y se crea la playlist.
8. La playlist se sincroniza a Spotify y se devuelve el enlace.
9. Las interacciones del usuario generan reward que retroalimenta el entrenamiento.

## 5. Modos de trabajo

### Modo online
Requiere cuenta Spotify, credenciales configuradas en `.env` y Docker corriendo.

### Modo offline
Independiente de APIs. Usa datos sintéticos para desarrollo y benchmarking.

```bash
uv run manage.py seed_synthetic_context
uv run manage.py seed_synthetic_interactions
uv run manage.py evaluate_model --with-synthetic-context --auto-train
```

## 6. Comandos esenciales para empezar

### Arranque

```bash
docker-compose up -d          # PostgreSQL + Redis
uv run manage.py migrate
uv run manage.py createsuperuser
uv run manage.py cities_light  # Importar ciudades de España
uv run manage.py runserver
```

### Generar una playlist real

```bash
uv run manage.py analyze_and_generate --username tu@email.com --max-tracks 500 --count 35
```

### Benchmark reproducible

```bash
uv run manage.py benchmark_matrix --config ml/benchmark_matrix_config.example.json
```

### Ayuda integrada

```bash
uv run manage.py moodsic_help
```

## 7. Dónde tocar código según el tipo de tarea

### Cambiar cómo se generan playlists
- `apps/interactions/services/playlist_generation_service.py`
- `apps/interactions/management/commands/analyze_and_generate.py`

### Cambiar la lógica de reward
- `apps/interactions/services/reward_service.py`
- `ml/reward.py`

### Cambiar el vector de estado del modelo
- `ml/state_builder.py`

### Cambiar las entradas de contexto (clima/noticias)
- `apps/context/services/weather_service.py`
- `apps/context/services/news_service.py`
- `apps/context/management/commands/refresh_context.py`

### Cambiar el perfil de usuario o el selector de ciudad
- `apps/users/views/profile_view.py`
- `templates/users/profile.html`

### Cambiar endpoints o payloads de la API
- `apps/interactions/views/`
- `apps/interactions/schemas.py`

## 8. Limitaciones conocidas

- **Audio features (403)**: Spotify deprecó `/v1/audio-features` en noviembre 2024 para apps no en la allowlist. El agente usa valores neutros (0.5) para esas features. No afecta al funcionamiento general.
- **Playlists propias (403)**: Requiere scope `playlist-read-private` en el token OAuth. `analyze_and_generate` continúa con las otras fuentes (liked, top, recent).
- **Base de datos geográfica**: Solo España (`CITIES_LIGHT_INCLUDE_COUNTRIES=['ES']`). Para añadir más países, actualizar esa configuración y re-ejecutar `cities_light`.

## 9. Estado actual (30 abril 2026)

- Autenticación OAuth Spotify: funcional.
- Recopilación de hasta 500 canciones: funcional (270+ reales obtenidas en prueba).
- Agente DQN: entrenado y operativo, genera playlists de 35 canciones.
- Clima real por ciudad del usuario: funcional (Open-Meteo).
- Selector de ciudad en perfil web con AJAX: funcional.
- Playlists sincronizadas a Spotify: funcional.
- Noticias reales via NewsAPI: funcional.
- Audio features: no disponibles (Spotify API deprecada).

## 10. Qué revisar en la primera hora

1. Este documento de onboarding.
2. `README.md` del repositorio.
3. `MANAGEMENT_COMMANDS.md`.
4. Swagger en `/api/interactions/docs/`.
5. `ml/state_builder.py` y `apps/interactions/management/commands/analyze_and_generate.py`.

## 2. Objetivo funcional

La idea principal es que el sistema no recomiende música de forma genérica, sino contextual:

- si el clima cambia, la selección puede adaptarse;
- si el usuario tiene un historial claro de gustos, ese patrón pesa en la decisión;
- si hay señales externas relevantes, el estado del recomendador también las incorpora.

## 3. Cómo se organiza el proyecto

### apps/users
Responsable de autenticación, perfiles de usuario y conexión con Spotify.

### apps/music
Gestiona el catálogo musical local: tracks, artistas, álbumes y operaciones de sincronización con Spotify.

### apps/context
Se encarga del contexto externo:
- clima;
- noticias;
- datos auxiliares de ciudad o localización.

### apps/interactions
Es el núcleo funcional del proyecto:
- genera playlists;
- registra interacciones del usuario;
- calcula reward;
- expone la API principal.

### apps/dashboard
Proporciona métricas y vistas agregadas para seguimiento del sistema.

### ml
Contiene la lógica del modelo de recomendación:
- agente DQN;
- state builder;
- reward matemático;
- entrenamiento y evaluación.

### pipelines
Incluye utilidades de ETL y preparación de datos/contexto.

## 4. Flujo principal del sistema

El recorrido típico es este:

1. el usuario solicita una playlist;
2. el sistema recupera contexto disponible;
3. se construye un estado numérico para el agente;
4. el recomendador ordena o selecciona tracks;
5. se crea la playlist local;
6. si Spotify está disponible, se sincroniza allí;
7. cuando el usuario interactúa, esa señal se convierte en reward y sirve para seguir entrenando.

## 5. Modos de trabajo

### Modo online
Se usa cuando hay credenciales válidas y servicios externos activos.

Aporta:
- sincronización con Spotify;
- noticias reales;
- contexto más cercano a producción.

### Modo offline
Se usa para desarrollo, pruebas y benchmarking.

Aporta:
- independencia de APIs externas;
- reproducibilidad;
- rapidez para iterar en el recomendador.

Actualmente este modo es una parte importante del flujo de trabajo del equipo.

## 6. Comandos que un compañero nuevo debería conocer primero

### Arranque básico

```bash
uv run manage.py migrate
uv run manage.py createsuperuser
uv run manage.py runserver
```

### Flujo offline mínimo

```bash
uv run manage.py seed_synthetic_context
uv run manage.py seed_synthetic_interactions
uv run manage.py evaluate_model --with-synthetic-context --auto-train
```

### Benchmark reproducible

```bash
uv run manage.py benchmark_matrix --config ml/benchmark_matrix_config.example.json
```

### Documentación de ayuda interna

```bash
uv run manage.py moodsic_help
```

## 7. Dónde tocar código según el tipo de tarea

### Si quieres cambiar cómo se generan playlists
Empieza por:
- apps/interactions/services/playlist_generation_service.py

### Si quieres cambiar la lógica de reward
Revisa:
- apps/interactions/services/reward_service.py
- ml/reward.py

### Si quieres cambiar el vector de estado del modelo
Revisa:
- ml/state_builder.py

### Si quieres tocar las entradas de contexto
Revisa:
- apps/context/services/news_service.py
- apps/context/services/weather_service.py
- pipelines/

### Si quieres tocar endpoints o payloads
Revisa:
- apps/interactions/views/
- apps/interactions/schemas.py
- apps/interactions/urls.py

## 8. Convenciones útiles del proyecto

- para demos y desarrollo se prioriza el flujo offline si las APIs no están disponibles;
- los artefactos locales de entrenamiento no deben entrar en el repositorio;
- la configuración ganadora actual del recomendador parte de una ponderación 0.6 para contexto y 0.4 para historial;
- antes de dar algo por correcto, se valida con comandos reales y tests.

## 9. Qué revisar en la primera hora

Una incorporación nueva puede orientarse muy rápido siguiendo este orden:

1. README principal del repositorio;
2. esta guía de onboarding;
3. MANAGEMENT_COMMANDS.md;
4. Swagger en /api/interactions/docs/;
5. el servicio de generación de playlists y el state builder.

## 10. Estado actual resumido

En el momento actual, el proyecto ya tiene:

- generación de playlists contextual;
- soporte híbrido offline y online;
- entrenamiento y evaluación del modelo;
- benchmarking con comparación de pesos y sensibilidad por alpha;
- tests automatizados cubriendo piezas clave.

## 11. Próximos focos de trabajo

Las siguientes líneas razonables de evolución son:

- mejorar aún más la señal que devuelve la API sobre si una playlist se generó con fallback u online real;
- seguir refinando el recomendador con datos más representativos;
- endurecer el paso a integración con servicios reales.

## 12. Flujo de demo recomendado para la entrega

Si alguien del equipo o el profesorado quiere revisar el proyecto en pocos minutos, el orden más claro es este:

1. abrir la ruta principal `/` o `/dashboard/` para ver el resumen del sistema;
2. entrar en Swagger en `/api/interactions/docs/`;
3. lanzar una generación de playlist y revisar los campos `mode`, `message` y `warnings`;
4. validar en el admin que las playlists e interacciones se han persistido correctamente.

## 13. Qué conviene explicar de forma honesta en la defensa

- el flujo offline está completo y permite entrenar, evaluar y hacer benchmark sin APIs reales;
- el backend distingue entre generación `online`, `fallback` e `hybrid`;
- Spotify real está preparado a nivel de integración, pero su validación final depende de credenciales/permisos externos.
