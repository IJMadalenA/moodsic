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

    @patch("spotipy.Spotify")
    def test_get_valid_token_not_expired(self, mock_spotify, user, _social_token):
        mock_spotify_instance = MagicMock()
        mock_spotify.return_value = mock_spotify_instance

        service = SpotifyMusicService(user)
        assert service.client is not None
        mock_spotify.assert_called_with(auth="old_access_token")

    @patch("spotipy.Spotify")
    @patch("apps.music.services.spotify_music_service.SpotifyOAuth")
    def test_get_valid_token_expired_refreshes(
        self, mock_oauth_class, mock_spotify, user, _social_token
    ):
        # Set token as expired (with more than 60s buffer)
        _social_token.expires_at = timezone.now() - timezone.timedelta(minutes=5)
        _social_token.save()

        # Mock OAuth and refresh response
        mock_oauth_instance = MagicMock()
        mock_oauth_class.return_value = mock_oauth_instance
        mock_oauth_instance.refresh_access_token.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600,
        }

        mock_spotify_instance = MagicMock()
        mock_spotify.return_value = mock_spotify_instance

        SpotifyMusicService(user)

        # Check SocialToken was updated
        _social_token.refresh_from_db()
        assert _social_token.token == "new_access_token"
        assert _social_token.token_secret == "new_refresh_token"

        # Check User model was updated
        user.refresh_from_db()
        assert user.access_token == "new_access_token"

        mock_oauth_instance.refresh_access_token.assert_called_with("refresh_token")
        # Should have been called with the new token
        mock_spotify.assert_called_with(auth="new_access_token")

    @patch("spotipy.Spotify")
    def test_get_user_info(self, mock_spotify, user, _social_token):
        mock_spotify_instance = MagicMock()
        mock_spotify.return_value = mock_spotify_instance
        mock_spotify_instance.current_user.return_value = {"id": "spotify_user_id"}

        service = SpotifyMusicService(user)
        info = service.get_user_info()

        assert info == {"id": "spotify_user_id"}
        # current_user is called twice: once during init and once in get_user_info()
        assert mock_spotify_instance.current_user.call_count >= 1

    @patch("spotipy.oauth2.SpotifyClientCredentials")
    @patch("spotipy.Spotify")
    def test_verify_api_connection_success(self, mock_spotify, _mock_creds):
        mock_spotify_instance = MagicMock()
        mock_spotify.return_value = mock_spotify_instance

        success, message = SpotifyMusicService.verify_api_connection()

        assert success is True
        assert "verified" in message.lower()

    @patch("spotipy.oauth2.SpotifyClientCredentials")
    @patch("spotipy.Spotify")
    def test_verify_api_connection_failure(self, mock_spotify, _mock_creds):
        mock_spotify.side_effect = Exception("API Error")

        success, message = SpotifyMusicService.verify_api_connection()

        assert success is False
        assert "API Error" in message
