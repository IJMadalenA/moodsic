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
