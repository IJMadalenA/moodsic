import socket
from unittest.mock import MagicMock, patch

import pytest
import requests
import spotipy
from django.utils import timezone

from apps.music.services.spotify_music_service import (
    NetworkAccessError,
    SpotifyMusicService,
)
from apps.users.models.user import User


@pytest.mark.django_db
class TestSpotifyServiceRobustness:
    @pytest.fixture
    def user(self):
        return User.objects.create_user(username="robust_user", email="robust@test.com")

    @patch("socket.gethostbyname")
    def test_check_network_access_success(self, mock_gethost):
        mock_gethost.return_value = "127.0.0.1"
        assert SpotifyMusicService.check_network_access() is True

    @patch("socket.gethostbyname")
    def test_check_network_access_failure(self, mock_gethost):
        mock_gethost.side_effect = socket.gaierror("Blocked")
        with pytest.raises(NetworkAccessError):
            SpotifyMusicService.check_network_access()

    @patch(
        "apps.music.services.spotify_music_service.SpotifyMusicService.get_spotify_client"
    )
    @patch(
        "apps.music.services.spotify_music_service.SpotifyMusicService.get_user_info"
    )
    def test_initialize_client_fail_user_info(
        self, mock_user_info, mock_get_client, user
    ):
        mock_get_client.return_value = MagicMock()
        mock_user_info.return_value = None
        service = SpotifyMusicService(user)
        assert service.client is None

    @patch(
        "apps.music.services.spotify_music_service.SpotifyMusicService.get_spotify_client"
    )
    def test_initialize_client_exception(self, mock_get_client, user):
        mock_get_client.side_effect = Exception("Crash")
        service = SpotifyMusicService(user)
        assert service.client is None

    def test_get_spotify_client_fallback_to_user(self, user):
        user.access_token = "user_token"
        user.save()
        service = SpotifyMusicService(user)
        client = service.get_spotify_client()
        assert client is not None
        # En el test real, como no hay SocialToken, usa el fallback

    @patch("apps.music.services.spotify_music_service.SpotifyOAuth")
    def test_refresh_token_process_no_secret(self, mock_oauth_class, user):
        from allauth.socialaccount.models import SocialAccount, SocialToken

        account = SocialAccount.objects.create(user=user, provider="spotify", uid="123")
        token = SocialToken.objects.create(account=account, token="t", token_secret="")

        mock_oauth_instance = MagicMock()
        mock_oauth_class.return_value = mock_oauth_instance

        service = SpotifyMusicService(user)
        service._refresh_token_process(token)
        # SpotifyOAuth se instancia pero refresh_access_token NO debe llamarse
        assert mock_oauth_instance.refresh_access_token.called is False

    @patch("apps.music.services.spotify_music_service.SocialToken.objects.filter")
    def test_get_spotify_client_exception(self, mock_filter, user):
        mock_filter.side_effect = Exception("DB Error")
        service = SpotifyMusicService(user)
        client = service.get_spotify_client()
        assert client is None

    @patch("apps.music.services.spotify_music_service.SpotifyOAuth")
    def test_refresh_token_process_exception(self, mock_oauth_class, user):
        from allauth.socialaccount.models import SocialAccount, SocialToken

        account = SocialAccount.objects.create(user=user, provider="spotify", uid="123")
        token = SocialToken.objects.create(account=account, token="t", token_secret="s")

        mock_oauth_instance = MagicMock()
        mock_oauth_class.return_value = mock_oauth_instance
        mock_oauth_instance.refresh_access_token.side_effect = Exception("API Down")

        service = SpotifyMusicService(user)
        service._refresh_token_process(token)
        # No debe explotar, solo loguear el error

    def test_add_tracks_to_playlist_no_tracks(self, user):
        service = SpotifyMusicService(user)
        assert service.add_tracks_to_playlist("id", []) is None

    @patch("spotipy.Spotify")
    def test_sync_playlist_success(self, mock_spotify, user):
        mock_instance = MagicMock()
        mock_spotify.return_value = mock_instance
        service = SpotifyMusicService(user)
        service.client = mock_instance

        # Mock create_playlist y add_tracks_to_playlist
        with (
            patch.object(
                service, "create_playlist", return_value={"id": "new_id"}
            ) as mock_create,
            patch.object(
                service, "add_tracks_to_playlist", return_value={"snapshot": "1"}
            ) as mock_add,
        ):
            result = service.sync_playlist("Name", "Desc", ["uri1"])
            assert result["id"] == "new_id"
            mock_create.assert_called_once()
            mock_add.assert_called_once()

    @patch("spotipy.Spotify")
    def test_sync_playlist_fail_create(self, mock_spotify, user):
        mock_instance = MagicMock()
        mock_spotify.return_value = mock_instance
        service = SpotifyMusicService(user)
        service.client = mock_instance

        with patch.object(service, "create_playlist", return_value=None):
            result = service.sync_playlist("Name", "Desc", ["uri1"])
            assert result is None

    @patch("apps.music.services.spotify_music_service.SocialToken.objects.get")
    def test_get_valid_token_expired_call_refresh(self, mock_get, user):
        from allauth.socialaccount.models import SocialToken

        mock_token = MagicMock(spec=SocialToken)
        mock_token.token = "old"
        mock_token.expires_at = timezone.now() - timezone.timedelta(seconds=10)
        mock_get.return_value = mock_token

        service = SpotifyMusicService(user)
        with patch.object(
            service, "_refresh_token_process", return_value="new"
        ) as mock_refresh:
            service._get_valid_token()
            assert mock_refresh.called

    @patch("spotipy.Spotify")
    def test_make_request_connection_error(self, mock_spotify, user):
        mock_instance = MagicMock()
        mock_spotify.return_value = mock_instance
        service = SpotifyMusicService(user)
        service.client = mock_instance

        mock_instance.current_user.side_effect = requests.exceptions.ConnectionError()
        with patch(
            "apps.music.services.spotify_music_service.SpotifyMusicService.check_network_access"
        ) as mock_check:
            with pytest.raises(requests.exceptions.ConnectionError):
                service._make_request("current_user")
            assert mock_check.called

    @patch("spotipy.Spotify")
    def test_make_request_unexpected_exception(self, mock_spotify, user):
        mock_instance = MagicMock()
        mock_spotify.return_value = mock_instance
        service = SpotifyMusicService(user)
        service.client = mock_instance

        mock_instance.current_user.side_effect = Exception("Unexpected")
        result = service._make_request("current_user")
        assert result is None

    def test_handle_spotify_exception_403(self, user):
        service = SpotifyMusicService(user)
        e = spotipy.exceptions.SpotifyException(
            http_status=403, code=-1, msg="Forbidden"
        )
        # No debe explotar
        service._handle_spotify_exception(e)

    @patch("spotipy.Spotify")
    def test_get_playlist_stats_no_playlist(self, mock_spotify, user):
        mock_instance = MagicMock()
        mock_spotify.return_value = mock_instance
        service = SpotifyMusicService(user)
        service.client = mock_instance
        mock_instance.playlist.return_value = None

        stats = service.get_playlist_stats("id")
        assert stats == {}

    @patch("spotipy.Spotify")
    def test_get_playlist_stats_with_data(self, mock_spotify, user):
        mock_instance = MagicMock()
        mock_spotify.return_value = mock_instance
        service = SpotifyMusicService(user)
        service.client = mock_instance
        mock_instance.playlist.return_value = {
            "name": "My Playlist",
            "owner": {"display_name": "Me"},
            "followers": {"total": 10},
            "tracks": {
                "total": 2,
                "items": [
                    {"track": {"duration_ms": 60000}},
                    {"track": {"duration_ms": 120000}},
                ],
            },
        }

        stats = service.get_playlist_stats("id")
        assert stats["name"] == "My Playlist"
        assert stats["total_tracks"] == 2
        assert stats["duration_minutes"] == 3

    @patch("spotipy.Spotify")
    def test_get_audio_features_batches(self, mock_spotify, user):
        mock_instance = MagicMock()
        mock_spotify.return_value = mock_instance
        service = SpotifyMusicService(user)
        service.client = mock_instance

        # Simulamos 150 tracks
        track_ids = [f"t{i}" for i in range(150)]
        mock_instance.audio_features.side_effect = [
            [{"id": f"t{i}"} for i in range(100)],
            [{"id": f"t{i}"} for i in range(100, 150)],
        ]

        features = service.get_audio_features(track_ids)
        assert len(features) == 150
        assert mock_instance.audio_features.call_count == 2
