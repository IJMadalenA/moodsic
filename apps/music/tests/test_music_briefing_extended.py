import pytest
from django.utils import timezone

from apps.context.models import WeatherContext
from apps.music.services.music_briefing_service import MusicBriefingService


@pytest.mark.django_db
class TestMusicBriefingService:
    def test_generate_briefing(self):
        from cities_light.models import Country, Region

        country = Country.objects.create(name="Spain", code2="ES")
        region = Region.objects.create(name="Madrid", country=country)

        weather = WeatherContext.objects.create(
            main_status="Clear",
            description="Sunny",
            temperature=25.0,
            feels_like=25.0,
            region=region,
            country=country,
            timestamp=timezone.now(),
        )

        briefing = MusicBriefingService.generate_briefing(weather)

        assert briefing["mood_name"] is not None
        assert "recommendation_params" in briefing
        assert briefing["recommendation_params"]["seed_genres"] is not None
        assert "Madrid" in briefing["context_summary"]
