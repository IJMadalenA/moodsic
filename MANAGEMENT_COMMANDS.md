# Comandos de gestión de MoodSic

Este documento resume todos los comandos `manage.py` disponibles, organizados por área funcional.

---

## 1. Comando principal: análisis y generación de playlist

### analyze_and_generate

Recopila hasta N canciones del historial de Spotify del usuario, obtiene el clima real de su ciudad y genera una playlist personalizada usando el agente RL. Crea y sincroniza la playlist directamente en Spotify.

```bash
uv run manage.py analyze_and_generate --username tu@email.com
```

**Opciones:**

| Opción | Por defecto | Descripción |
|--------|-------------|-------------|
| `--username` | — | Email del usuario (obligatorio) |
| `--max-tracks` | `500` | Número máximo de canciones a recopilar |
| `--count` | `35` | Canciones en la playlist generada |
| `--name` | Auto | Nombre de la playlist (ej. "MoodSic · Mix Real 30 Abr") |
| `--include-playlists` | `5` | Nº de playlists propias del usuario a incluir |
| `--dry-run` | `False` | Simula sin crear nada en Spotify ni en BD |

**Fuentes de canciones:**
- Liked tracks (hasta 500 con paginación)
- Top tracks (short/medium/long term)
- Recently played (últimas 50)
- Playlists propias (requiere scope `playlist-read-private`)

**Ejemplo completo:**
```bash
uv run manage.py analyze_and_generate \
    --username ana@ejemplo.com \
    --max-tracks 500 \
    --count 35 \
    --name "MoodSic Verano"
```

---

## 2. Comandos de contexto

### refresh_context

Actualiza el clima y las noticias para las ciudades de los usuarios activos. Si ningún usuario tiene ciudad configurada, usa ciudades por defecto (Madrid, Barcelona).

```bash
uv run manage.py refresh_context
```

### seed_synthetic_context

Genera contexto sintético de clima y noticias para desarrollo y demos sin depender de APIs externas.

```bash
uv run manage.py seed_synthetic_context --weather-count 60 --news-count 120 --days-back 7
```

### fetch_news_context

Obtiene noticias reales desde NewsAPI y las persiste en la base de datos.

```bash
uv run manage.py fetch_news_context --query "music OR artists" --category music
```

---

## 3. Comandos de catálogo e interacciones

### seed_synthetic_interactions

Crea interacciones sintéticas entre usuarios y tracks para poblar el sistema sin datos reales.

```bash
uv run manage.py seed_synthetic_interactions --users 3 --tracks 30 --interactions 600
```

### sync_spotify_tracks

Sincroniza tracks desde Spotify al catálogo local de un usuario.

```bash
uv run manage.py sync_spotify_tracks --user-id 1 --limit 100
```

### collect_interactions

Recopila y resume métricas de interacciones registradas.

```bash
uv run manage.py collect_interactions --days 7 --generate-report
```

---

## 4. Comandos de entrenamiento y evaluación

### train_agent

Entrena el agente RL usando interacciones de la base de datos. Puede combinarse con datos sintéticos.

```bash
uv run manage.py train_agent --episodes 20 --days 30 --save
uv run manage.py train_agent --with-synthetic-context --episodes 5 --save
```

### evaluate_model

Evalúa un modelo guardado o entrena uno rápido para benchmark.

```bash
uv run manage.py evaluate_model --model-path ml/models/dqn_agent_20260430_163358.h5
uv run manage.py evaluate_model --with-synthetic-context --auto-train --benchmark-episodes 5
```

---

## 5. Comandos de benchmarking

### benchmark_summary

Genera un resumen en Markdown o CSV de benchmarks recientes, con ranking, tendencia y robustez.

```bash
uv run manage.py benchmark_summary --limit 10 --output ml/logs/benchmark_summary.md
uv run manage.py benchmark_summary --w-accuracy 0.6 --w-reward 0.4 --robustness-alpha 0.5
```

### benchmark_matrix

Ejecuta barridos reproducibles por seeds, pesos y alpha. También acepta archivo de configuración JSON.

```bash
uv run manage.py benchmark_matrix --config ml/benchmark_matrix_config.example.json
uv run manage.py benchmark_matrix --seeds 101,202,303 --weights 0.6:0.4,0.7:0.3 --alphas 0.25,0.5,1.0
```

---

## 6. Datos geográficos

### cities_light

Descarga e importa la base de datos de ciudades de GeoNames. Configurado para importar solo España (`CITIES_LIGHT_INCLUDE_COUNTRIES=['ES']`, ~544 ciudades). Necesario para el selector de ciudad del perfil de usuario.

```bash
uv run manage.py cities_light
```

---

## 7. Ayuda integrada

### moodsic_help

Muestra ayuda de los comandos principales del proyecto.

```bash
uv run manage.py moodsic_help
uv run manage.py moodsic_help --command train_agent
```

---

## Flujos recomendados

### Generar playlist con datos reales (modo online)

```bash
# 1. Asegurar contexto actualizado
uv run manage.py refresh_context

# 2. Generar playlist
uv run manage.py analyze_and_generate --username tu@email.com --max-tracks 500 --count 35
```

### Demo offline rápida

```bash
uv run manage.py seed_synthetic_context
uv run manage.py seed_synthetic_interactions
uv run manage.py evaluate_model --with-synthetic-context --auto-train
```

### Evaluación comparativa reproducible

```bash
uv run manage.py benchmark_matrix --config ml/benchmark_matrix_config.example.json
```

---

## Recomendaciones prácticas

- Para desarrollo local, prioriza el flujo offline si no tienes las APIs disponibles.
- No subas artefactos generados en `ml/logs/` ni `ml/models/` al repositorio.
- Usa `benchmark_matrix` cuando quieras comparar configuraciones, no solo entrenar una vez.
- La configuración ganadora actual del recomendador parte de 0.6 contexto y 0.4 historial.
- El modelo activo es `ml/models/dqn_agent_20260430_163358.h5`.
