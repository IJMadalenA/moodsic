from unittest.mock import MagicMock, patch

import pytest
from allauth.socialaccount.models import SocialAccount, SocialToken
from django.utils import timezone

from apps.music.services.spotify_music_service import SpotifyMusicService
from apps.users.models.user import User


@pytest.mark.django_db
class TestSpotifyMusicServiceEnhancements:
    @pytest.fixture
    def user(self):
        return User.objects.create_user(
            username="testuser_enh", email="test_enh@example.com"
        )

    @pytest.fixture
    def _social_token(self, user):
        account = SocialAccount.objects.create(
            user=user, provider="spotify", uid="spotify_user_id_enh"
        )
        return SocialToken.objects.create(
            account=account,
            token="access_token",
            token_secret="refresh_token",
            expires_at=timezone.now() + timezone.timedelta(hours=1),
        )

    @patch("spotipy.Spotify")
    def test_search_tracks_with_audio_features(self, mock_spotify, user, _social_token):
        mock_spotify_instance = MagicMock()
        mock_spotify.return_value = mock_spotify_instance
        mock_spotify_instance.search.return_value = {
            "tracks": {"items": [{"id": "track_1", "name": "Track 1"}]}
        }

        service = SpotifyMusicService(user)
        # Probamos búsqueda con género y parámetros de audio
        results = service.search_tracks(
            query="genre:rock",
            limit=10,
            min_energy=0.5,
            max_valence=0.8,
            min_danceability=0.6,
        )

        assert results["tracks"]["items"][0]["id"] == "track_1"
        # Verificamos que se llamó a search con el query correcto
        # Nota: Spotify search API no soporta parámetros de audio directamente en el query de 'search'
        # pero spotipy.recommendations sí los soporta.
        # Si queremos usar search tradicional con filtros avanzados, hay que ver si es posible.
        # Spotify search soporta filtros como 'genre:', 'year:', 'artist:', 'album:'.
        # Los parámetros técnicos (energy, valence) suelen usarse en 'recommendations'.
        # El requerimiento dice: "Implementar el método de búsqueda de canciones que permita filtrar por género y, sobre todo, por parámetros de audio".
        # Si 'search' no lo permite, quizás deba filtrar los resultados después o usar 'recommendations'.
        # Sin embargo, 'recommendations' requiere semillas (seeds).
        # Vamos a ver si el requerimiento implica usar 'recommendations' o una búsqueda + filtrado.
        # Normalmente para parámetros técnicos se usa 'recommendations'.

        mock_spotify_instance.search.assert_called_once()

    @patch("spotipy.Spotify")
    def test_get_recommendations(self, mock_spotify, user, _social_token):
        mock_spotify_instance = MagicMock()
        mock_spotify.return_value = mock_spotify_instance
        mock_spotify_instance.recommendations.return_value = {
            "tracks": [{"id": "rec_track_1", "name": "Rec Track 1"}]
        }

        service = SpotifyMusicService(user)
        results = service.get_recommendations(
            seed_genres=["rock"], limit=5, target_energy=0.7, target_valence=0.5
        )

        assert results["tracks"][0]["id"] == "rec_track_1"
        mock_spotify_instance.recommendations.assert_called_once()
