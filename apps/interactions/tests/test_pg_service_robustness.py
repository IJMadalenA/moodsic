from unittest.mock import patch

import pytest

from apps.context.models import NewsContext, WeatherContext
from apps.interactions.services.playlist_generation_service import (
    PlaylistGenerationService,
)
from apps.music.models import Album, Track
from apps.users.models.user import User


@pytest.mark.django_db
class TestPGServiceRobustness:
    @pytest.fixture
    def service(self):
        return PlaylistGenerationService()

    @pytest.fixture
    def user(self):
        return User.objects.create_user(username="pg_user", email="pg@test.com")

    @pytest.fixture
    def track(self):
        album = Album.objects.create(name="A", spotify_id="al1")
        track = Track.objects.create(
            name="T", spotify_id="t1", album=album, track_number=1, duration_ms=1000
        )
        return track

    def test_get_track_audio_features_empty(self, service, track):
        features = service._get_track_audio_features(track)
        assert features["energy"] == 0.5  # Default value

    def test_record_interaction_full(self, service, user, track):
        from django.utils import timezone

        weather = WeatherContext.objects.create(
            temperature=20.0,
            feels_like=19.0,
            humidity=50,
            wind_speed=5.0,
            main_status="Clear",
            description="sky",
            timestamp=timezone.now(),
        )
        news = NewsContext.objects.create(
            title="News", sentiment_score=0.8, sentiment_label="Positive"
        )

        with patch.object(
            service.reward_service, "calculate_interaction_reward", return_value=1.0
        ):
            result = service.record_interaction(
                user=user,
                track=track,
                feedback="completed",
                play_duration=100,
                track_duration=100,
                session_id="sess1",
                weather_id=weather.id,
                news_ids=[news.id],
            )
            assert result["reward"] == 1.0
            assert result["is_positive"] is True

    def test_get_user_stats_empty(self, service, user):
        stats = service.get_user_stats(user)
        assert stats["total_interactions"] == 0
        assert stats["average_reward"] == 0.0

    def test_resolve_generation_mode(self, service):
        assert service._resolve_generation_mode({"used_spotify_sync": True}) == "online"
        assert (
            service._resolve_generation_mode({"used_local_catalog": True}) == "fallback"
        )
        assert (
            service._resolve_generation_mode(
                {"used_spotify_sync": True, "used_local_catalog": True}
            )
            == "hybrid"
        )
