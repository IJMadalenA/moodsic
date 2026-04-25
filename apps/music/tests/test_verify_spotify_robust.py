from unittest.mock import patch

import pytest
from django.core.management import call_command


@pytest.mark.django_db
class TestVerifySpotifyCommand:
    @patch("apps.music.management.commands.verify_spotify.SpotifyMusicService")
    def test_verify_spotify_success(self, mock_service_class):
        mock_service_class.verify_api_connection.return_value = (
            True,
            "Connection verified.",
        )
        call_command("verify_spotify")
        assert mock_service_class.verify_api_connection.called

    @patch("apps.music.management.commands.verify_spotify.SpotifyMusicService")
    def test_verify_spotify_failure(self, mock_service_class):
        mock_service_class.verify_api_connection.return_value = (
            False,
            "Connection failed.",
        )
        call_command("verify_spotify")
        assert mock_service_class.verify_api_connection.called
