import pytest
from cities_light.models import Country

from apps.context.models.weather_context import WeatherContext
from apps.music.services.music_briefing_service import MusicBriefingService


@pytest.mark.django_db
class TestMusicBriefingService:
    def test_generate_briefing_clear_weather(self):
        # Setup
        country = Country.objects.create(name="Spain", code2="ES")
        weather = WeatherContext(
            country=country,
            main_status="Clear",
            temperature=25.0,
            description="Cielo despejado",
        )

        # Action
        briefing = MusicBriefingService.generate_briefing(weather)

        # Assertions
        assert briefing["mood_name"] == "Happy/Upbeat"
        assert briefing["recommendation_params"]["target_energy"] == 0.8
        assert "pop" in briefing["recommendation_params"]["seed_genres"]
        assert "Spain" in briefing["context_summary"]
        assert "25.0" in briefing["context_summary"]

    def test_generate_briefing_rain_weather(self):
        # Setup
        country = Country.objects.create(name="UK", code2="GB")
        weather = WeatherContext(
            country=country,
            main_status="Rain",
            temperature=12.0,
            description="Lluvia ligera",
        )

        # Action
        briefing = MusicBriefingService.generate_briefing(weather)

        # Assertions
        assert briefing["mood_name"] == "Melancholic/Cozy"
        assert briefing["recommendation_params"]["target_energy"] == 0.3
        assert "jazz" in briefing["recommendation_params"]["seed_genres"]
        assert "UK" in briefing["context_summary"]

    def test_generate_briefing_unknown_weather_defaults_to_clouds(self):
        # Setup
        country = Country.objects.create(name="Mars", code2="MR")
        weather = WeatherContext(
            country=country,
            main_status="Sandstorm",  # No mapeado
            temperature=-60.0,
            description="Tormenta de arena",
        )

        # Action
        briefing = MusicBriefingService.generate_briefing(weather)

        # Assertions
        # Debería usar el default de MoodService (Clouds)
        assert briefing["mood_name"] == "Chill/Calm"
        assert briefing["recommendation_params"]["target_energy"] == 0.4
        assert "chill" in briefing["recommendation_params"]["seed_genres"]
