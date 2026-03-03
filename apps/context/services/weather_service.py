import logging
from datetime import datetime
from typing import ClassVar

import requests
from cities_light.models import City
from django.conf import settings
from django.utils import timezone

from ..models import WeatherContext


class WeatherService:
    """
    Servicio para interactuar con la API de Open-Meteo.
    Proporciona datos meteorológicos gratuitos sin necesidad de API Key.
    """

    WMO_CODES: ClassVar[dict[int, tuple[str, str]]] = {
        0: ("Clear", "Cielo despejado"),
        1: ("Clouds", "Principalmente despejado"),
        2: ("Clouds", "Parcialmente nublado"),
        3: ("Clouds", "Cubierto"),
        45: ("Fog", "Niebla"),
        48: ("Fog", "Niebla con escarcha"),
        51: ("Drizzle", "Llovizna ligera"),
        53: ("Drizzle", "Llovizna moderada"),
        55: ("Drizzle", "Llovizna densa"),
        56: ("Drizzle", "Llovizna helada ligera"),
        57: ("Drizzle", "Llovizna helada densa"),
        61: ("Rain", "Lluvia ligera"),
        63: ("Rain", "Lluvia moderada"),
        65: ("Rain", "Lluvia fuerte"),
        66: ("Rain", "Lluvia helada ligera"),
        67: ("Rain", "Lluvia helada fuerte"),
        71: ("Snow", "Nieve ligera"),
        73: ("Snow", "Nieve moderada"),
        75: ("Snow", "Nieve fuerte"),
        77: ("Snow", "Granos de nieve"),
        80: ("Rain", "Lluvia intermitente ligera"),
        81: ("Rain", "Lluvia intermitente moderada"),
        82: ("Rain", "Lluvia intermitente violenta"),
        85: ("Snow", "Nieve intermitente ligera"),
        86: ("Snow", "Nieve intermitente fuerte"),
        95: ("Thunderstorm", "Tormenta"),
        96: ("Thunderstorm", "Tormenta con granizo ligero"),
        99: ("Thunderstorm", "Tormenta con granizo fuerte"),
    }

    @classmethod
    def fetch_and_store_weather(cls, city: City):
        """
        Consulta la API de Open-Meteo usando las coordenadas de una ciudad específica y guarda el resultado.
        """
        base_url = getattr(
            settings, "OPENMETEO_BASE_URL", "https://api.open-meteo.com/v1/forecast"
        )

        if not city.latitude or not city.longitude:
            raise ValueError(
                f"La ciudad {city.name} no tiene coordenadas configuradas."
            )

        params = {
            "latitude": city.latitude,
            "longitude": city.longitude,
            "current": [
                "temperature_2m",
                "relative_humidity_2m",
                "apparent_temperature",
                "is_day",
                "precipitation",
                "rain",
                "showers",
                "snowfall",
                "weather_code",
                "cloud_cover",
                "pressure_msl",
                "surface_pressure",
                "wind_speed_10m",
                "wind_direction_10m",
                "wind_gusts_10m",
            ],
            "daily": [
                "temperature_2m_max",
                "temperature_2m_min",
                "sunrise",
                "sunset",
            ],
            "timezone": "auto",
            "forecast_days": 1,
        }

        try:
            response = requests.get(base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            logging.getLogger(__name__).error(f"Error al consultar Open-Meteo: {e}")
            raise

        current = data.get("current", {})
        daily = data.get("daily", {})
        weather_code = current.get("weather_code", 0)
        status, description = cls.WMO_CODES.get(
            weather_code, ("Unknown", "Desconocido")
        )

        def get_dt(dt_str):
            if not dt_str:
                return None
            try:
                # Open-Meteo returns ISO 8601 strings
                dt = datetime.fromisoformat(dt_str)
                return timezone.make_aware(dt) if timezone.is_naive(dt) else dt
            except ValueError:
                return None

        # Mapeo al modelo WeatherContext
        weather_context = WeatherContext.objects.create(
            city=city,
            region=city.region,
            country=city.country,
            main_status=status,
            description=description,
            icon_code=str(weather_code),
            temperature=current.get("temperature_2m"),
            feels_like=current.get("apparent_temperature"),
            temp_min=daily.get("temperature_2m_min", [None])[0]
            if daily.get("temperature_2m_min")
            else None,
            temp_max=daily.get("temperature_2m_max", [None])[0]
            if daily.get("temperature_2m_max")
            else None,
            pressure=int(current.get("pressure_msl", 0))
            if current.get("pressure_msl") is not None
            else None,
            humidity=current.get("relative_humidity_2m"),
            wind_speed=current.get("wind_speed_10m"),
            wind_deg=current.get("wind_direction_10m"),
            wind_gust=current.get("wind_gusts_10m"),
            clouds_all=current.get("cloud_cover"),
            rain_1h=float(current.get("rain", 0.0) or 0.0)
            + float(current.get("showers", 0.0) or 0.0),
            snow_1h=float(current.get("snowfall", 0.0) or 0.0),
            timestamp=get_dt(current.get("time")) or timezone.now(),
            sunrise=get_dt(daily.get("sunrise", [None])[0])
            if daily.get("sunrise")
            else None,
            sunset=get_dt(daily.get("sunset", [None])[0])
            if daily.get("sunset")
            else None,
        )

        return weather_context
