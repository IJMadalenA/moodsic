import logging

from cities_light.models import City
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from apps.context.services.news_service import NewsService
from apps.context.services.weather_service import WeatherService

logger = logging.getLogger(__name__)


@receiver(user_logged_in)
def automate_context_on_login(sender, request, user, **kwargs):
    """
    Al hacer login, se cargan los datos que alimentarán el MoodService.
    """
    logger.info(f"🚀 Iniciando automatización para el usuario: {user.username}")

    # 1. Cargar Noticias (Independiente de la ciudad)
    try:
        NewsService.fetch_and_store_news()
        logger.info("✅ Noticias actualizadas.")
    except Exception as e:
        logger.error(f"❌ Error cargando noticias: {e}")

    # 2. Cargar Clima (Necesita una ciudad)
    try:
        # Buscamos Madrid como ciudad por defecto para las pruebas
        city = City.objects.filter(name="Madrid").first() or City.objects.first()

        if city:
            WeatherService.fetch_and_store_weather(city)
            logger.info(f"✅ Clima para {city.name} actualizado.")
        else:
            logger.warning(
                "⚠️ No se encontró ninguna ciudad en la DB. El clima no se cargó."
            )

    except Exception as e:
        logger.error(f"❌ Error cargando clima: {e}")
