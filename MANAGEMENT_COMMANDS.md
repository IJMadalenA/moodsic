# Comandos de gestión de MoodSic

Este documento resume los comandos más importantes para trabajar con el proyecto, especialmente en desarrollo local y en modo offline.

## 1. Comandos de contexto

### seed_synthetic_context
Genera contexto sintético de clima y noticias para desarrollo, demos y entrenamiento offline.

```bash
uv run manage.py seed_synthetic_context --weather-count 60 --news-count 120 --days-back 7
```

### fetch_news_context
Obtiene noticias desde el proveedor configurado y las persiste en la base de datos.

```bash
uv run manage.py fetch_news_context --query "music OR artists" --category music
```

## 2. Comandos de interacciones y catálogo

### seed_synthetic_interactions
Crea interacciones sintéticas entre usuarios y tracks, útiles para poblar el sistema sin depender de datos reales.

```bash
uv run manage.py seed_synthetic_interactions --users 3 --tracks 30 --interactions 600
```

### sync_spotify_tracks
Sincroniza tracks desde Spotify al catálogo local.

```bash
uv run manage.py sync_spotify_tracks --user-id 1 --limit 100
```

### collect_interactions
Recopila y resume métricas de interacciones registradas.

```bash
uv run manage.py collect_interactions --days 7 --generate-report
```

## 3. Comandos de entrenamiento y evaluación

### train_agent
Entrena el agente RL usando interacciones de base de datos. Puede combinarse con datos sintéticos.

```bash
uv run manage.py train_agent --episodes 20 --days 30 --save
uv run manage.py train_agent --with-synthetic-context --episodes 5 --save
```

### evaluate_model
Evalúa un modelo guardado o entrena uno rápido para benchmark si se usa con auto-train.

```bash
uv run manage.py evaluate_model --model-path ml/models/model.h5
uv run manage.py evaluate_model --with-synthetic-context --auto-train --benchmark-episodes 5
```

## 4. Comandos de benchmarking

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

## 5. Comando de ayuda

### moodsic_help
Muestra ayuda integrada de los comandos principales.

```bash
uv run manage.py moodsic_help
uv run manage.py moodsic_help --command train_agent
```

## Flujos recomendados

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

### Trabajo con APIs reales

```bash
uv run manage.py sync_spotify_tracks --user-id 1 --limit 100
uv run manage.py fetch_news_context --query "music OR entertainment" --category music
```

## Recomendaciones prácticas

- Para desarrollo local, prioriza primero el flujo offline.
- No subas artefactos generados en ml/logs ni ml/models.
- Usa benchmark_matrix cuando quieras comparar configuraciones, no solo entrenar una vez.
- La configuración ganadora actual del recomendador parte de 0.6 contexto y 0.4 historial.
