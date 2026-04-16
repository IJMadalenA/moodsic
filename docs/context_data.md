# Contexto y Datos Externos

Este documento detalla cómo Moodsic gestiona los datos del entorno (clima, ubicación, tendencias) para alimentar su motor de recomendaciones.

## 1. Datos Geográficos (cities_light)

Moodsic utiliza `django-cities-light` para mantener una base de datos local de países, regiones y ciudades de todo el mundo. Esto permite mapear la ubicación del usuario a coordenadas geográficas sin depender de APIs externas para cada búsqueda.

### Configuración
En `config/settings.py` se han configurado los siguientes filtros para el MVP (enfocado inicialmente en mercados hispanohablantes):
- **Países incluidos**: España (ES), México (MX), Argentina (AR), Colombia (CO), Chile (CL), Perú (PE).
- **Idiomas de traducción**: Español e Inglés.

### Comando de Automatización
Para facilitar la población de estos datos durante la instalación o migraciones, se ha creado un comando personalizado:
```bash
uv run manage.py setup_geo
```
Este comando:
1. Ejecuta las migraciones necesarias para `cities_light`.
2. Descarga y procesa los datos de GeoNames de forma desatendida.

---

## 2. Información Climática (Open-Meteo)

La obtención de datos climáticos se realiza mediante la API de **Open-Meteo**, que ofrece datos precisos de forma gratuita y sin necesidad de API Key.

### Modelo `WeatherContext`
Ubicado en `apps/context/models/weather_context.py`, este modelo almacena:
- **Ubicación**: Relación con `City`, `Region` y `Country`.
- **Estado**: Descripción del clima (ej: "Llovizna ligera") y código WMO.
- **Métricas**: Temperatura, sensación térmica, humedad, presión, viento, nubosidad y precipitación.
- **Momentos**: Timestamp de la medición, amanecer y atardecer.

### Servicio `WeatherService`
Ubicado en `apps/context/services/weather_service.py`, este servicio proporciona el método principal:
- `fetch_and_store_weather(city)`: Consulta Open-Meteo usando las coordenadas de la ciudad y guarda un registro en `WeatherContext`.

### Gestión en el Panel de Administración

Moodsic utiliza **Django Unfold** para visualizar y gestionar el contexto climático y geográfico desde el panel administrativo.

#### Acciones de Geografía (`CityAdmin`)
En la lista de ciudades (`/admin/cities_light/city/`), se ha habilitado un botón para la sincronización de datos:
- **Botón "Actualizar Datos Geográficos"**: Ubicado en la barra superior de la lista (esquina derecha). Al presionarlo, ejecuta el comando `setup_geo`, que actualiza la base de datos de países, regiones y ciudades según la configuración de `settings.py`.

#### Acciones del Admin (`WeatherContextAdmin`)
En la lista de contextos climáticos (`/admin/context/weathercontext/`), se han habilitado herramientas para actualizar datos en tiempo real:
- **Botón "Actualizar clima (Global)"**: Ubicado en la barra superior de la lista. Al presionarlo, el sistema selecciona automáticamente una muestra de ciudades (inicialmente las primeras 10 con coordenadas) y descarga sus datos climáticos actuales.
- **Acción de lista "Actualizar clima para ciudades seleccionadas"**: Permite seleccionar registros existentes y forzar una actualización del clima para las ciudades vinculadas a esos registros.

---

## 3. Próximos Pasos (En desarrollo)
- **News API Integration**: Servicio para capturar noticias relevantes por región.
- **Mood Mapper**: Lógica para transformar códigos climáticos y noticias en "Moods" consumibles por el agente de Spotify.
- **Periodic Pipeline**: Automatización de la actualización del clima para usuarios activos.
