from secrets import compare_digest
from unittest.mock import MagicMock, patch

import pytest
from allauth.socialaccount.models import SocialAccount, SocialToken
from django.utils import timezone

from apps.music.services.spotify_music_service import SpotifyMusicService
from apps.users.models.user import User


@pytest.mark.django_db
class TestSpotifyMusicService:
    @pytest.fixture
    def user(self):
        return User.objects.create_user(username="testuser", email="test@example.com")

    @pytest.fixture
    def _social_token(self, user):
        account = SocialAccount.objects.create(
            user=user, provider="spotify", uid="spotify_user_id"
        )
        return SocialToken.objects.create(
            account=account,
            token="old_access_token",
            token_secret="refresh_token",
            expires_at=timezone.now() + timezone.timedelta(hours=1),
        )

    def test_get_valid_token_not_expired(self, user, _social_token):
        service = SpotifyMusicService(user)
        token = service._get_valid_token()
        assert compare_digest(token.token, "old_access_token")
        assert token.id == _social_token.id

    @patch("apps.music.services.spotify_music_service.SpotifyOAuth")
    def test_get_valid_token_expired_refreshes(
        self, mock_oauth_class, user, _social_token
    ):
        # Set token as expired
        _social_token.expires_at = timezone.now() - timezone.timedelta(minutes=1)
        _social_token.save()

        # Mock OAuth and refresh response
        mock_oauth_instance = MagicMock()
        mock_oauth_class.return_value = mock_oauth_instance
        mock_oauth_instance.refresh_access_token.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600,
        }

        service = SpotifyMusicService(user)
        token = service._get_valid_token()

        assert compare_digest(token.token, "new_access_token")
        assert token.token_secret == "new_refresh_token"
        assert token.expires_at > timezone.now()
        mock_oauth_instance.refresh_access_token.assert_called_with("refresh_token")

    @patch("spotipy.Spotify")
    def test_get_user_info(self, mock_spotify, user, _social_token):
        mock_spotify_instance = MagicMock()
        mock_spotify.return_value = mock_spotify_instance
        mock_spotify_instance.current_user.return_value = {"id": "spotify_user_id"}

        service = SpotifyMusicService(user)
        info = service.get_user_info()

        assert info == {"id": "spotify_user_id"}
        mock_spotify_instance.current_user.assert_called_once()

    @patch("spotipy.oauth2.SpotifyClientCredentials")
    @patch("spotipy.Spotify")
    def test_verify_api_connection_success(self, mock_spotify, _mock_creds):
        mock_spotify_instance = MagicMock()
        mock_spotify.return_value = mock_spotify_instance

        success, message = SpotifyMusicService.verify_api_connection()

        assert success is True
        assert "Conexión exitosa" in message

    @patch("spotipy.oauth2.SpotifyClientCredentials")
    @patch("spotipy.Spotify")
    def test_verify_api_connection_failure(self, mock_spotify, _mock_creds):
        mock_spotify.side_effect = Exception("API Error")

        success, message = SpotifyMusicService.verify_api_connection()

        assert success is False
        assert "Error de conexión" in message
