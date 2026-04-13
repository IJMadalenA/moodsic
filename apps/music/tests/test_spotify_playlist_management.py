from unittest.mock import MagicMock, patch

import pytest
import spotipy
from allauth.socialaccount.models import SocialAccount, SocialToken
from django.utils import timezone

from apps.music.services.spotify_music_service import SpotifyMusicService
from apps.users.models.user import User


@pytest.mark.django_db
class TestSpotifyPlaylistManagement:
    @pytest.fixture
    def user(self):
        return User.objects.create_user(
            username="test_playlist_user", email="test_playlist@example.com"
        )

    @pytest.fixture
    def _social_token(self, user):
        account = SocialAccount.objects.create(
            user=user, provider="spotify", uid="spotify_playlist_uid"
        )
        return SocialToken.objects.create(
            account=account,
            token="access_token",
            token_secret="refresh_token",
            expires_at=timezone.now() + timezone.timedelta(hours=1),
        )

    @patch("spotipy.Spotify")
    def test_create_playlist(self, mock_spotify, user, _social_token):
        mock_instance = MagicMock()
        mock_spotify.return_value = mock_instance
        mock_instance.current_user.return_value = {"id": "spotify_user_id"}
        mock_instance.user_playlist_create.return_value = {
            "id": "new_playlist_id",
            "name": "Moodsic: Happy",
        }

        service = SpotifyMusicService(user)
        playlist = service.create_playlist(
            name="Moodsic: Happy", description="Created by Moodsic"
        )

        assert playlist["id"] == "new_playlist_id"
        mock_instance.user_playlist_create.assert_called_once_with(
            user="spotify_user_id",
            name="Moodsic: Happy",
            public=True,
            collaborative=False,
            description="Created by Moodsic",
        )

    @patch("spotipy.Spotify")
    def test_add_tracks_to_playlist(self, mock_spotify, user, _social_token):
        mock_instance = MagicMock()
        mock_spotify.return_value = mock_instance
        mock_instance.playlist_add_items.return_value = {"snapshot_id": "snap_1"}

        service = SpotifyMusicService(user)
        track_uris = ["spotify:track:1", "spotify:track:2"]
        result = service.add_tracks_to_playlist("playlist_id", track_uris)

        assert result["snapshot_id"] == "snap_1"
        mock_instance.playlist_add_items.assert_called_once_with(
            "playlist_id", track_uris
        )

    @patch("spotipy.Spotify")
    def test_replace_playlist_tracks(self, mock_spotify, user, _social_token):
        mock_instance = MagicMock()
        mock_spotify.return_value = mock_instance
        mock_instance.playlist_replace_items.return_value = {"snapshot_id": "snap_2"}

        service = SpotifyMusicService(user)
        track_uris = ["spotify:track:3", "spotify:track:4"]
        result = service.replace_playlist_tracks("playlist_id", track_uris)

        assert result["snapshot_id"] == "snap_2"
        mock_instance.playlist_replace_items.assert_called_once_with(
            "playlist_id", track_uris
        )

    @patch("spotipy.Spotify")
    @patch("apps.music.services.spotify_music_service.logger")
    def test_handle_rate_limit(self, mock_logger, mock_spotify, user, _social_token):
        mock_instance = MagicMock()
        mock_spotify.return_value = mock_instance

        # Simulamos error 429
        exception = spotipy.SpotifyException(
            http_status=429,
            code=-1,
            msg="Rate limit exceeded",
            headers={"Retry-After": "30"},
        )
        mock_instance.playlist_add_items.side_effect = exception

        service = SpotifyMusicService(user)
        result = service.add_tracks_to_playlist("playlist_id", ["uri"])

        assert result is None
        mock_logger.error.assert_any_call(
            "Límite de tasa (Rate Limit) alcanzado. Reintentar después de 30s."
        )

    @patch("spotipy.Spotify")
    def test_handle_expired_token(self, mock_spotify, user, _social_token):
        mock_instance = MagicMock()
        mock_spotify.return_value = mock_instance

        # Simulamos error 401
        exception = spotipy.SpotifyException(
            http_status=401, code=-1, msg="Unauthorized"
        )
        mock_instance.playlist_add_items.side_effect = exception

        service = SpotifyMusicService(user)

        # Al fallar con 401, debería intentar refrescar (aunque no reintenta la operación automáticamente en esta versión simplificada)
        # pero el cliente debería ser recreado.
        with patch.object(
            service, "_get_valid_token", return_value=_social_token
        ) as mock_refresh:
            result = service.add_tracks_to_playlist("playlist_id", ["uri"])
            assert result is None
            mock_refresh.assert_called()
