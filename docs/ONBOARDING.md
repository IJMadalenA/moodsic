# Guía de onboarding de MoodSic

Esta guía está pensada para una persona que entra nueva al proyecto y necesita entender rápido qué hace MoodSic, cómo está organizado y por dónde empezar.

## 1. Resumen ejecutivo

MoodSic es una plataforma que genera playlists personalizadas combinando:

- catálogo musical;
- preferencias e historial del usuario;
- contexto externo como clima, noticias y momento del día;
- un recomendador basado en aprendizaje por refuerzo.

El proyecto está diseñado para poder avanzar incluso cuando no se dispone de APIs reales o datos de usuarios, gracias a un modo offline con contexto e interacciones sintéticas.

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
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Flujo offline mínimo

```bash
python manage.py seed_synthetic_context
python manage.py seed_synthetic_interactions
python manage.py evaluate_model --with-synthetic-context --auto-train
```

### Benchmark reproducible

```bash
python manage.py benchmark_matrix --config ml/benchmark_matrix_config.example.json
```

### Documentación de ayuda interna

```bash
python manage.py moodsic_help
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
