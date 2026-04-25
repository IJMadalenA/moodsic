import pytest

from apps.context.models import NewsContext
from apps.interactions.services.playlist_generation_service import (
    PlaylistGenerationService,
)
from apps.music.models import Album, Artist, Track
from apps.users.models.user import User


@pytest.mark.django_db
class TestPlaylistGenerationExtended:
    @pytest.fixture
    def service(self):
        return PlaylistGenerationService()

    @pytest.fixture
    def user(self):
        return User.objects.create_user(username="pg_ext", email="pg_ext@test.com")

    @pytest.fixture
    def track(self):
        artist = Artist.objects.create(name="Artist")
        album = Album.objects.create(name="Album")
        t = Track.objects.create(
            spotify_id="t_pg_1",
            name="Track",
            duration_ms=200000,
            track_number=1,
            album=album,
        )
        t.artists.add(artist)
        return t

    def test_score_track_with_news(self, service, track):
        weather_context = {"main_status": "Clear", "temperature": 25}
        user_history = {"avg_energy": 0.5, "avg_danceability": 0.5, "avg_valence": 0.5}

        # Primero sin noticias
        score_no_news = service._score_track(track, weather_context, user_history)

        # Ahora con noticias positivas
        NewsContext.objects.create(
            title="Happy", sentiment_score=0.9, is_breaking=False, url="h1"
        )
        # El servicio busca noticias de la categoria 'general' por defecto en _get_latest_news_contexts

        score_with_news = service._score_track(track, weather_context, user_history)
        # El score debería ser igual porque _score_track no usa noticias directamente en su logica interna
        # sino que las noticias se usan para construir el briefing que se pasa a Spotify (si se usa modo online)
        # o se inyectan en el weather_context para el Reward.
        assert score_with_news == score_no_news

    def test_get_user_history_no_interactions(self, service, user):
        history = service._get_user_history(user)
        assert history["avg_energy"] == 0.5
        assert history["favorite_genres"] == []

    def test_sync_playlist_to_spotify_no_tracks(self, service, user):
        from apps.music.models import Playlist

        playlist = Playlist.objects.create(user=user, name="Empty")
        result = service._sync_playlist_to_spotify(user, playlist, [])
        assert result is None
