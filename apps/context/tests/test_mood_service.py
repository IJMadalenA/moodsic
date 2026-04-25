from apps.context.services.mood_service import MoodService


def test_mood_service_clear():
    params = MoodService.get_music_params_for_weather("Clear")
    assert params["target_energy"] == 0.8
    assert "pop" in params["seed_genres"]
    assert MoodService.get_mood_name("Clear") == "Happy/Upbeat"


def test_mood_service_rain():
    params = MoodService.get_music_params_for_weather("Rain")
    assert params["target_energy"] == 0.3
    assert "jazz" in params["seed_genres"]
    assert MoodService.get_mood_name("Rain") == "Melancholic/Cozy"


def test_mood_service_unknown():
    # Debería devolver por defecto "Clouds" (Chill/Calm)
    params = MoodService.get_music_params_for_weather("UnknownStatus")
    assert params["target_energy"] == 0.4
    assert MoodService.get_mood_name("UnknownStatus") == "Chill/Calm"


def test_mood_service_snow():
    params = MoodService.get_music_params_for_weather("Snow")
    assert params["target_energy"] == 0.2
    assert MoodService.get_mood_name("Snow") == "Peaceful/Winter"


def test_mood_service_thunderstorm():
    params = MoodService.get_music_params_for_weather("Thunderstorm")
    assert params["target_energy"] == 0.9
    assert MoodService.get_mood_name("Thunderstorm") == "Dark/Aggressive"


def test_mood_service_drizzle():
    params = MoodService.get_music_params_for_weather("Drizzle")
    assert params["target_energy"] == 0.4
    assert MoodService.get_mood_name("Drizzle") == "Reflective"


def test_mood_service_fog():
    params = MoodService.get_music_params_for_weather("Fog")
    assert params["target_energy"] == 0.3
    assert MoodService.get_mood_name("Fog") == "Mysterious"


def test_mood_service_get_combined_params():
    # Caso neutral
    params = MoodService.get_combined_params("Clear", 0.0)
    assert params["target_energy"] == 0.8
    assert params["target_valence"] == 0.8

    # Sentimiento positivo (debería subir valence)
    params = MoodService.get_combined_params("Clear", 0.8)
    # base 0.8 + (0.8 * 0.25) = 1.0
    assert params["target_valence"] == 1.0
    # abs(0.8) > 0.6 -> energy sube 0.15: 0.8 + 0.15 = 0.95
    assert params["target_energy"] == 0.95

    # Sentimiento negativo (debería bajar valence)
    params = MoodService.get_combined_params("Clear", -0.8)
    # base 0.8 + (-0.8 * 0.25) = 0.6
    assert params["target_valence"] == 0.6
    # abs(-0.8) > 0.6 -> energy sube 0.15: 0.8 + 0.15 = 0.95
    assert params["target_energy"] == 0.95

    # Caso por defecto (Clouds)
    params = MoodService.get_combined_params("Unknown", 0.0)
    assert params["target_energy"] == 0.4
    assert params["target_valence"] == 0.5


def test_mood_service_get_mood_name_with_sentiment():
    # Positivo fuerte
    assert MoodService.get_mood_name("Clear", 0.5) == "Very Positive & Happy/Upbeat"
    # Negativo fuerte
    assert MoodService.get_mood_name("Clear", -0.5) == "Somber & Happy/Upbeat"
    # Neutral
    assert MoodService.get_mood_name("Clear", 0.0) == "Happy/Upbeat"
    # Desconocido
    assert MoodService.get_mood_name("Unknown", 0.5) == "Very Positive & Chill/Calm"
