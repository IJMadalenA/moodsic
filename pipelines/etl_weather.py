"""ETL helpers for weather ingestion."""

from cities_light.models import City

from apps.context.services.weather_service import WeatherService


def run_weather_etl(limit: int = 10) -> int:
    """Fetch and store weather for top cities with coordinates.

    Returns the number of successful city updates.
    """
    cities = City.objects.filter(latitude__isnull=False, longitude__isnull=False)[
        :limit
    ]
    count = 0
    for city in cities:
        WeatherService.fetch_and_store_weather(city)
        count += 1
    return count
