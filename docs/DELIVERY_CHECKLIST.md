# Checklist de entrega y defensa de MoodSic

Este documento sirve para alinear la memoria, la demo y la explicación oral con lo que el código implementa realmente a día de hoy.

## 1. Qué se puede afirmar con seguridad

### Funcionalidades implementadas
- generación de playlists personalizadas;
- registro de interacciones y cálculo de reward;
- uso de contexto meteorológico y de noticias;
- entrenamiento y evaluación del recomendador;
- benchmarking reproducible en modo offline;
- respuesta de API con trazabilidad del modo usado: `online`, `fallback` o `hybrid`.

### Evidencias prácticas
- panel de demo disponible en la raíz `/` y en `/dashboard/`;
- Swagger operativo en `/api/interactions/docs/`;
- persistencia en base de datos local y revisión desde `/admin/`.

## 2. Qué conviene explicar como limitación real

- Spotify en modo real depende de credenciales válidas y permisos externos;
- NewsAPI puede funcionar en fallback local si no hay clave activa;
- el proyecto está especialmente preparado para desarrollo y demo offline reproducible.

## 3. Demo mínima recomendada

1. abrir la portada del proyecto;
2. enseñar Swagger y el endpoint de generación de playlists;
3. generar una playlist con contexto activado;
4. comentar los campos `mode`, `message` y `warnings` de la respuesta;
5. mostrar en el admin que la playlist y la interacción quedan registradas.

## 4. Relación entre objetivos académicos y código

| Objetivo académico | Dónde se ve en el proyecto |
| :--- | :--- |
| Recomendación personalizada | apps/interactions/services/playlist_generation_service.py |
| Aprendizaje por refuerzo | ml/agent.py, ml/reward.py, ml/state_builder.py, ml/training.py |
| Integración de contexto | apps/context/services, apps/context/models |
| API usable y demostrable | apps/interactions/views, apps/interactions/schemas.py |
| Evaluación y comparación | benchmark_matrix, benchmark_summary |

## 5. Mensaje final recomendado para la defensa

MoodSic no se queda en una maqueta estática: el sistema ya es capaz de generar playlists, registrar feedback, recalcular reward y trabajar de forma robusta incluso sin APIs reales, lo que permitió avanzar y validar el núcleo del proyecto de forma reproducible.
