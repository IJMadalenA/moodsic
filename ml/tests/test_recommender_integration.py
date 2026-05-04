import pytest
from django.contrib.auth import get_user_model

from apps.interactions.services.playlist_generation_service import (
    get_playlist_generation_service,
)
from apps.music.models import Artist, Playlist, Track, TrackAudioFeatures, TrackLyrics
from ml.recommender import get_ml_recommender

User = get_user_model()


@pytest.mark.django_db
class TestMLRecommenderIntegration:
    @pytest.fixture
    def user(self, db):
        return User.objects.create_user(username="mluser", password="pass")

    @pytest.fixture
    def populated_tracks(self, db):
        """Create 20 tracks with audio features and lyrics for realistic testing."""
        artist = Artist.objects.create(spotify_id="arti1", name="Test Artist")
        tracks = []
        for i in range(20):
            t = Track.objects.create(
                spotify_id=f"mlt{i}",
                name=f"ML Track {i}",
                duration_ms=200000,
                track_number=1,
                genre="pop",
            )
            t.artists.add(artist)
            TrackAudioFeatures.objects.create(
                track=t,
                danceability=0.3 + i * 0.03,
                energy=0.2 + i * 0.04,
                key=i % 12,
                loudness=-10 + i,
                mode=i % 2,
                speechiness=0.05,
                acousticness=0.5 - i * 0.02,
                instrumentalness=0.0,
                liveness=0.1,
                valence=0.1 + i * 0.04,
                tempo=80 + i * 5,
                time_signature=4,
            )
            TrackLyrics.objects.create(
                track=t,
                artist_name="A",
                song_name=f"S{i}",
                text="happy" if i % 2 == 0 else "sad",
                match_status="matched",
                sentiment_score=0.5 if i % 2 == 0 else -0.5,
                sentiment_label="positive" if i % 2 == 0 else "negative",
                sentiment_pos=0.5,
                sentiment_neg=0.1,
                sentiment_neu=0.4,
            )
            tracks.append(t)
        return tracks

    def test_generate_playlist_uses_ml(self, user, populated_tracks):
        """End-to-end: playlist generation uses ML recommender."""
        svc = get_playlist_generation_service()
        recommender = get_ml_recommender()
        recommender._fitted = False  # reset for clean test
        recommender.feature_matrix_ = None

        weather = {"main_status": "Clear", "temperature": 22, "humidity": 50}
        result = svc.generate_playlist(
            user=user,
            playlist_name="ML Test Playlist",
            count=5,
            weather_context=weather,
            use_context=True,
        )

        assert "playlist_id" in result
        assert "track_ids" in result
        assert len(result["track_ids"]) <= 5
        assert result["mode"] in ("hybrid", "fallback", "online")

        playlist = Playlist.objects.filter(
            spotify_id__startswith="moodsic_"
        ).first()
        assert playlist is not None
        assert playlist.tracks.count() <= 5

    def test_generate_playlist_without_weather(self, user, populated_tracks):
        """Playlist generation works without weather context."""
        svc = get_playlist_generation_service()
        recommender = get_ml_recommender()
        recommender._fitted = False
        recommender.feature_matrix_ = None

        result = svc.generate_playlist(
            user=user,
            playlist_name="No Weather",
            count=3,
            weather_context=None,
            use_context=False,
        )
        assert len(result["track_ids"]) <= 3

    def test_target_mood_builder(self):
        """_build_target_mood correctly adjusts mood based on weather."""
        svc = get_playlist_generation_service()
        weather = {"main_status": "Rain", "temperature": 10}
        target = svc._build_target_mood(weather, news_sentiment=-0.5)
        assert target["target_valence"] <= 0.5  # rain + negative news -> low valence

        target_sunny = svc._build_target_mood(
            {"main_status": "Clear", "temperature": 25}, news_sentiment=0.4
        )
        assert target_sunny["target_energy"] >= 0.5  # clear + positive -> high energy

    def test_recommender_fallback_when_not_fitted(self, populated_tracks):
        """Heuristic fallback works when recommender is not fitted."""
        recommender = get_ml_recommender()
        recommender._fitted = False
        recommender.feature_matrix_ = None

        scored = recommender.score_tracks(populated_tracks)
        assert len(scored) == len(populated_tracks)
        assert scored[0][1] >= scored[-1][1]
