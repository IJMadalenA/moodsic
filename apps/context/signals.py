import logging
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from apps.context.services.weather_service import WeatherService
from apps.context.services.news_service import NewsService
from cities_light.models import City, Country
from apps.music.services.spotify_music_service import SpotifyMusicService

logger = logging.getLogger(__name__)

def ensure_default_city():
    """
    Verifica si hay ciudades en la DB. Si no, crea una por defecto (Madrid).
    Esto evita tener que usar la consola de comandos.
    """
    city = City.objects.filter(name="Madrid").first() or City.objects.first()
    
    if not city:
        logger.info("🌍 No se encontraron ciudades. Creando Madrid por defecto...")
        country, _ = Country.objects.get_or_create(name="Spain", code2="ES")
        city, _ = City.objects.get_or_create(
            name="Madrid",
            country=country,
            defaults={'latitude': 40.4168, 'longitude': -3.7038}
        )
    return city

@receiver(user_logged_in)
def automate_context_on_login(sender, request, user, **kwargs):
    """
    Al hacer login, se generan automáticamente todos los contextos necesarios.
    """
    logger.info(f"🚀 Login detectado para: {user.username}. Automatizando contextos...")

    # 1. Asegurar que existe al menos una ciudad y cargar Clima
    try:
        city = ensure_default_city()
        WeatherService.fetch_and_store_weather(city)
        logger.info(f"✅ Clima para {city.name} actualizado automáticamente.")
    except Exception as e:
        logger.error(f"❌ Error automático en Clima: {e}")

    # 2. Cargar Noticias
    try:
        NewsService.fetch_and_store_news()
        logger.info("✅ Noticias actualizadas automáticamente.")
    except Exception as e:
        logger.error(f"❌ Error automático en Noticias: {e}")

    # 3. Cargar Música desde Spotify
    try:
        # Inicializamos el servicio de Spotify para este usuario
        sp_service = SpotifyMusicService(user)
        
        if sp_service.client:
            logger.info(f"🎵 Poblando música para {user.username}...")
            # Sincroniza tracks, artistas y álbumes
            sp_service.sync_user_top_tracks() 
            logger.info("✅ Música del usuario sincronizada.")
        else:
            logger.warning(f"⚠️ No se pudo conectar con Spotify para {user.username} (¿Token faltante?)")
            
    except Exception as e:
        logger.error(f"❌ Error automático en Música: {e}")