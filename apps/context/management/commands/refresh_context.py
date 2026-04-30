from cities_light.models import City
from django.core.management.base import BaseCommand

from apps.context.services.news_service import NewsService
from apps.context.services.weather_service import WeatherService


# Default cities with coordinates for when cities_light has no data
_DEFAULT_CITIES = [
    {"name": "Madrid", "country_code": "ES", "latitude": 40.4168, "longitude": -3.7038},
    {"name": "Barcelona", "country_code": "ES", "latitude": 41.3851, "longitude": 2.1734},
]


class _StubCity:
    """Minimal city-like object with coordinates, used as fallback when cities_light has no data."""

    class _StubCountry:
        def __init__(self, code):
            self.code2 = code

    def __init__(self, name, country_code, latitude, longitude):
        self.name = name
        self.country = self._StubCountry(country_code)
        self.latitude = latitude
        self.longitude = longitude


class Command(BaseCommand):
    help = "Actualiza el clima y las noticias en la base de datos"

    def handle(self, *args, **options):
        # Actualizar noticias
        self.stdout.write("Actualizando noticias...")
        try:
            NewsService.fetch_and_store_news()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error actualizando noticias: {e}"))

        # Actualizar clima de ciudades con usuarios activos
        self.stdout.write("Actualizando clima...")

        # Obtener ciudades únicas de usuarios
        cities = list(City.objects.filter(user__is_active=True).distinct())

        # Si no hay ciudades de usuarios, usar ciudades por defecto
        if not cities:
            self.stdout.write(
                "No hay ciudades vinculadas a usuarios activos. Usando ciudades por defecto..."
            )
            for city_data in _DEFAULT_CITIES:
                db_city = City.objects.filter(name=city_data["name"]).first()
                if db_city:
                    cities.append(db_city)
                else:
                    cities.append(
                        _StubCity(
                            name=city_data["name"],
                            country_code=city_data["country_code"],
                            latitude=city_data["latitude"],
                            longitude=city_data["longitude"],
                        )
                    )

        # Procesar ciudades
        processed_cities = 0
        for city in cities:
            try:
                self.stdout.write(
                    f"Actualizando clima para {city.name}..."
                )
                WeatherService.fetch_and_store_weather(city)
                processed_cities += 1
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error actualizando clima para {city.name}: {e}")
                )

        if processed_cities > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Contexto actualizado correctamente ({processed_cities} ciudades)"
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING("No se pudo actualizar el clima para ninguna ciudad")
            )
