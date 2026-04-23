from datetime import timedelta

from django.utils import timezone

from ..models import NewsContext, WeatherContext
from .news_service import NewsService
from .weather_service import WeatherService


class ContextManager:
    """Orquesta la actualización automática de clima y noticias."""

    @staticmethod
    def get_current_context(city, force_refresh=False):
        """
        Obtiene el contexto actual. Si los datos tienen más de 30 minutos, 
        los actualiza automáticamente.
        """
        now = timezone.now()
        threshold = now - timedelta(minutes=30)

        # 1. Gestionar Clima
        weather = WeatherContext.objects.filter(city=city, timestamp__gte=threshold).first()
        if not weather or force_refresh:
            try:
                weather = WeatherService.fetch_and_store_weather(city)
            except Exception:
                weather = WeatherContext.objects.filter(city=city).first() # Fallback al último conocido

        # 2. Gestionar Noticias
        news = NewsContext.objects.filter(published_at__gte=threshold)
        if not news.exists() or force_refresh:
            try:
                NewsService.fetch_and_store_news()
                news = NewsContext.objects.order_by("-published_at")[:10]
            except Exception:
                news = NewsContext.objects.order_by("-published_at")[:10] # Fallback

        return {
            "weather": weather,
            "news": news,
            "timestamp": now
        }
