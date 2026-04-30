# Contexto y Datos Externos

Este documento detalla cómo MoodSic gestiona los datos del entorno (clima, ubicación, noticias) para alimentar el motor de recomendaciones.

---

## 1. Datos Geográficos (cities_light)

MoodSic usa `django-cities-light` para mantener una base de datos local de países y ciudades con coordenadas. Esto permite obtener clima real de cualquier ciudad sin depender de APIs de geocodificación.

### Configuración actual (`config/settings.py`)

```python
CITIES_LIGHT_INCLUDE_COUNTRIES = ['ES']       # Solo España
CITIES_LIGHT_TRANSLATION_LANGUAGES = ['es', 'en']
```

La BD contiene ~544 ciudades españolas.

### Importar datos

```bash
uv run manage.py cities_light
```

Los datos se descargan de GeoNames y se almacenan localmente. Ejecuciones posteriores solo actualizan cambios incrementales.

### Selector de ciudad en el perfil

El usuario puede configurar su ciudad desde `/accounts/profile/`. El campo `User.city` es una FK a `cities_light.City`. El perfil incluye:

- campo de texto con autocompletado AJAX (`/accounts/profile/cities/?q=...`);
- botón "Guardar ciudad" que hace POST a `/accounts/profile/update/`;
- botón "Quitar ciudad" para eliminar la asociación.

Una vez configurada, el sistema obtiene el clima de las coordenadas de esa ciudad. Sin ciudad configurada, `refresh_context` usa Madrid y Barcelona como respaldo.

---

## 2. Clima (Open-Meteo)

MoodSic obtiene datos climáticos de **Open-Meteo** — API gratuita sin API key.

### Modelo `WeatherContext` (`apps/context/models/weather_context.py`)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `city` | FK → City | Ciudad a la que corresponde el dato |
| `temperature` | float | Temperatura en °C |
| `feels_like` | float | Sensación térmica en °C |
| `humidity` | int | Humedad relativa en % |
| `wind_speed` | float | Velocidad del viento km/h |
| `pressure` | float | Presión atmosférica hPa |
| `visibility` | float (nullable) | Visibilidad en metros (Open-Meteo no siempre la devuelve) |
| `clouds_all` | int | Cobertura de nubes en % |
| `rain_1h` | float | Precipitación en la última hora mm |
| `main_status` | str | Estado principal (Clear, Clouds, Rain…) |
| `description` | str | Descripción textual |
| `timestamp` | datetime | Momento de la medición |

### Servicio `WeatherService` (`apps/context/services/weather_service.py`)

Método principal:

```python
WeatherService.fetch_and_store_weather(city: City) -> WeatherContext
```

Construye la URL de Open-Meteo con `city.latitude` y `city.longitude`, parsea la respuesta y guarda un nuevo `WeatherContext`.

### Comando `refresh_context`

```bash
uv run manage.py refresh_context
```

1. Consulta `City.objects.filter(user__is_active=True).distinct()` para obtener las ciudades de los usuarios activos.
2. Si la lista está vacía, usa las ciudades por defecto (Madrid y Barcelona).
3. Para cada ciudad, llama a `WeatherService.fetch_and_store_weather()` y a los proveedores de noticias.

### Integración con el agente RL

El comando `analyze_and_generate` obtiene el `WeatherContext` más reciente (o lo refresca si tiene más de 60 minutos) y construye el dict que pasa al `StateBuilder`:

```python
weather_context_dict = {
    "temperature": latest_wc.temperature or 20.0,
    "feels_like": latest_wc.feels_like or 20.0,
    "humidity": latest_wc.humidity or 60,
    "wind_speed": latest_wc.wind_speed or 0.0,
    "pressure": latest_wc.pressure or 1013.0,
    "visibility": latest_wc.visibility or 10000,
    "clouds_all": latest_wc.clouds_all or 0,
    "rain_1h": latest_wc.rain_1h or 0.0,
    "main_status": latest_wc.main_status or "Clear",
}
```

El `StateBuilder._extract_weather_features()` lee exactamente estos nombres de campo.

---

## 3. Noticias (NewsAPI)

MoodSic obtiene noticias desde **NewsAPI** usando la clave configurada en `NEWSAPI_KEY`.

### Servicio de noticias (`apps/context/services/news_service.py`)

Llama a `/v2/top-headlines?country=us` y persiste los resultados como `NewsContext`.

### Comando manual

```bash
uv run manage.py fetch_news_context --query "music OR artists" --category music
```

---

## 4. Estado actual (30 abril 2026)

| Servicio | Estado | Notas |
|---------|--------|-------|
| Open-Meteo (clima) | Operativo | Sin API key, gratuito |
| NewsAPI (noticias) | Operativo | Requiere `NEWSAPI_KEY` |
| cities_light (geografía) | Operativo | Solo España, ~544 ciudades |
| Selector de ciudad en perfil | Operativo | Autocompletado AJAX funcional |
| Audio features Spotify | No disponible | API deprecada por Spotify desde nov. 2024 |
