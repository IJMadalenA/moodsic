from typing import ClassVar, TypedDict


class MusicParameters(TypedDict, total=False):
    target_energy: float
    target_valence: float
    target_danceability: float
    seed_genres: list[str]


class MoodService:
    """
    Servicio para normalizar estados climáticos a Moods y parámetros musicales.
    """

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
    def get_music_params_for_weather(
        cls, main_status: str
    ) -> str | dict[str, float | list[str]]:
        """
        Dada una condición climática principal, devuelve los parámetros musicales sugeridos.
        """
        mapping = cls.MOOD_MAPPING.get(main_status, cls.MOOD_MAPPING["Clouds"])
        return mapping["params"]

    @classmethod
    def get_mood_name(cls, main_status: str) -> str:
        """
        Devuelve el nombre del mood para una condición climática.
        """
        mapping = cls.MOOD_MAPPING.get(main_status, cls.MOOD_MAPPING["Clouds"])
        return mapping["mood"]
