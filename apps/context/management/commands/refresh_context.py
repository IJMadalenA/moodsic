from cities_light.models import City
from django.core.management.base import BaseCommand

from apps.context.services.news_service import NewsService
from apps.context.services.weather_service import WeatherService


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
            for city_name in ["Madrid", "Barcelona", "Valencia"]:
                city = City.objects.filter(name=city_name).first()
                if city:
                    cities.append(city)

        # Procesar ciudades
        processed_cities = 0
        for city in cities:
            try:
                self.stdout.write(
                    f"Actualizando clima para {city.name} ({city.country.code2})..."
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
