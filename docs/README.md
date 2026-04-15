# Índice de documentación de MoodSic

Esta carpeta agrupa la documentación útil para entender el proyecto sin tener que recorrer todo el código desde cero.

## Documentos principales

| Documento | Para qué sirve |
| :--- | :--- |
| [ONBOARDING.md](ONBOARDING.md) | Guía de entrada rápida para una persona nueva en el proyecto. |
| [INTEGRATION_PLAN_DEV.md](INTEGRATION_PLAN_DEV.md) | Orden y criterios técnicos para integrar ramas y revisar cambios. |
| [../README.md](../README.md) | Visión general del producto, stack, arranque y mapa del repositorio. |
| [../DEVELOPMENT.md](../DEVELOPMENT.md) | Estado funcional y guía rápida de desarrollo. |
| [../MANAGEMENT_COMMANDS.md](../MANAGEMENT_COMMANDS.md) | Referencia de comandos operativos, entrenamiento y benchmarking. |

## Si acabas de incorporarte al proyecto

Se recomienda leer en este orden:

1. [../README.md](../README.md)
2. [ONBOARDING.md](ONBOARDING.md)
3. [../MANAGEMENT_COMMANDS.md](../MANAGEMENT_COMMANDS.md)
4. Swagger de la API en /api/interactions/docs/

## Qué encontrarás en el código

- apps/users: autenticación e integración con Spotify.
- apps/music: catálogo musical y servicios Spotify.
- apps/context: clima, noticias y contexto externo.
- apps/interactions: lógica principal de recomendación y feedback.
- ml: agente RL, reward, entrenamiento y evaluación.
- pipelines: ETL y preparación de contexto.
