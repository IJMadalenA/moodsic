from django.core.management.base import BaseCommand
from apps.context.services.weather_service import WeatherService
from apps.context.services.news_service import NewsService
from cities_light.models import City

class Command(BaseCommand):
    help = "Actualiza el clima y las noticias en la base de datos"

    def handle(self, *args, **options):
        # Actualizar noticias
        self.stdout.write("Actualizando noticias...")
        NewsService.fetch_and_store_news()
        
        # Actualizar clima de ciudades principales (ejemplo)
        self.stdout.write("Actualizando clima...")
        for city_name in ["Madrid", "Barcelona", "Valencia"]:
            city = City.objects.filter(name=city_name).first()
            if city:
                WeatherService.fetch_and_store_weather(city)
        
        self.stdout.write(self.style.SUCCESS("Contexto actualizado correctamente"))