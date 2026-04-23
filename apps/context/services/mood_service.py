from typing import ClassVar, TypedDict
import logging

logger = logging.getLogger(__name__)

class MusicParameters(TypedDict, total=False):
    """Estructura de parámetros para la API de recomendaciones de Spotify."""
    target_energy: float
    target_valence: float
    target_danceability: float
    seed_genres: list[str]

class MoodService:
    """
    Servicio avanzado para normalizar estados climáticos y sentimientos de noticias
    en parámetros musicales técnicos para Spotify.
    """

    # Diccionario base que mapea el clima a estados de ánimo y parámetros iniciales
    MOOD_MAPPING: ClassVar[dict[str, dict]] = {
        "Clear": {
            "mood": "Happy/Upbeat",
            "params": {
                "target_energy": 0.8,
                "target_valence": 0.8,
                "target_danceability": 0.7,
                "seed_genres": ["pop", "happy", "dance"],
            },
        },
        "Clouds": {
            "mood": "Chill/Calm",
            "params": {
                "target_energy": 0.4,
                "target_valence": 0.5,
                "target_danceability": 0.3,
                "seed_genres": ["chill", "ambient", "acoustic"],
            },
        },
        "Rain": {
            "mood": "Melancholic/Cozy",
            "params": {
                "target_energy": 0.3,
                "target_valence": 0.3,
                "target_danceability": 0.2,
                "seed_genres": ["jazz", "blues", "rainy-day"],
            },
        },
        "Drizzle": {
            "mood": "Reflective",
            "params": {
                "target_energy": 0.4,
                "target_valence": 0.4,
                "target_danceability": 0.3,
                "seed_genres": ["indie", "folk"],
            },
        },
        "Thunderstorm": {
            "mood": "Dark/Aggressive",
            "params": {
                "target_energy": 0.9,
                "target_valence": 0.2,
                "target_danceability": 0.5,
                "seed_genres": ["metal", "rock", "industrial"],
            },
        },
        "Snow": {
            "mood": "Peaceful/Winter",
            "params": {
                "target_energy": 0.2,
                "target_valence": 0.6,
                "target_danceability": 0.1,
                "seed_genres": ["classical", "piano"],
            },
        },
        "Fog": {
            "mood": "Mysterious",
            "params": {
                "target_energy": 0.3,
                "target_valence": 0.4,
                "target_danceability": 0.2,
                "seed_genres": ["trip-hop", "ambient"],
            },
        },
    }

    @classmethod
    def get_combined_params(cls, main_status: str, avg_sentiment: float = 0.0) -> MusicParameters:
        """
        Calcula los parámetros finales ajustando la base del clima con el 
        sentimiento de las noticias (rango de -1.0 a 1.0).
        """
        # 1. Obtener la configuración base según el clima
        mapping = cls.MOOD_MAPPING.get(main_status, cls.MOOD_MAPPING["Clouds"])
        params: MusicParameters = mapping["params"].copy()
        
        # 2. Ajuste de VALENCE (Felicidad musical) según noticias
        # El sentimiento de las noticias modifica la felicidad de la música
        valence_adjustment = avg_sentiment * 0.25
        new_valence = params.get("target_valence", 0.5) + valence_adjustment
        params["target_valence"] = max(0.0, min(1.0, round(new_valence, 2)))
        
        # 3. Ajuste de ENERGY según intensidad de noticias
        # Si las noticias son muy extremas (muy buenas o muy malas), subimos la energía
        if abs(avg_sentiment) > 0.6:
            new_energy = params.get("target_energy", 0.5) + 0.15
            params["target_energy"] = max(0.0, min(1.0, round(new_energy, 2)))

        logger.info(
            f"Mood Engine -> Clima: {main_status}, Sentimiento: {avg_sentiment:.2f} | "
            f"Resultado -> Valence: {params['target_valence']}, Energy: {params['target_energy']}"
        )
        
        return params

    @classmethod
    def get_mood_label(cls, main_status: str, avg_sentiment: float = 0.0) -> str:
        """
        Genera una etiqueta de texto descriptiva del estado de ánimo combinado.
        """
        base_mood = cls.MOOD_MAPPING.get(main_status, cls.MOOD_MAPPING["Clouds"])["mood"]
        
        if avg_sentiment > 0.4:
            return f"Very Positive & {base_mood}"
        elif avg_sentiment < -0.4:
            return f"Somber & {base_mood}"
        
        return base_mood

    @classmethod
    def get_music_params_for_weather(cls, main_status: str) -> MusicParameters:
        """
        Método legado: mantiene compatibilidad devolviendo solo la base del clima.
        """
        mapping = cls.MOOD_MAPPING.get(main_status, cls.MOOD_MAPPING["Clouds"])
        return mapping["params"]