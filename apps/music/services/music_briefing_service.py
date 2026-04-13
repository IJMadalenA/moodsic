import logging
from typing import Any

from apps.context.models.weather_context import WeatherContext
from apps.context.services.mood_service import MoodService

logger = logging.getLogger(__name__)


class MusicBriefingService:
    """
    Servicio de orquestación que genera el 'Briefing Musical' completo.
    Combina datos de contexto (clima, ubicación) para producir los parámetros
    que Spotify necesita para generar recomendaciones.
    """

    @staticmethod
    def generate_briefing(weather: WeatherContext) -> dict[str, Any]:
        """
        Genera un diccionario con todos los parámetros necesarios para SpotifyMusicService.get_recommendations.
        """
        # 1. Obtener parámetros basados en el clima (Mood Mapping)
        mood_params = MoodService.get_music_params_for_weather(weather.main_status)
        mood_name = MoodService.get_mood_name(weather.main_status)

        # 2. Construir el briefing
        # Nota: Por ahora usamos los seed_genres definidos en el MoodMapping.
        # En el futuro, podríamos inyectar seeds basados en la región del usuario.
        briefing = {
            "mood_name": mood_name,
            "recommendation_params": {
                "limit": 20,
                "seed_genres": mood_params.get("seed_genres", ["pop"]),
                "target_energy": mood_params.get("target_energy"),
                "target_valence": mood_params.get("target_valence"),
                "target_danceability": mood_params.get("target_danceability"),
            },
            "context_summary": f"Clima en {weather.region or weather.country}: {weather.main_status} ({weather.temperature}°C)",
        }

        logger.info(
            f"Briefing musical generado para {weather.main_status}: {mood_name}"
        )
        return briefing
