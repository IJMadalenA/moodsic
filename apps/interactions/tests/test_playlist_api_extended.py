from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model

from apps.music.models import Playlist, Track

User = get_user_model()


@pytest.mark.django_db
class TestPlaylistAPIExtended:
    @pytest.fixture
    def client(self):
        from django.test import Client

        return Client()

    @pytest.fixture
    def user(self):
        return User.objects.create_user(
            username="playlist_api_user",
            email="playlist_api@test.com",
            is_spotify_connected=True,
        )

    def test_generate_playlist_unauthorized(self, client):
        url = "/api/interactions/playlists/generate/"
        payload = {"count": 10}
        response = client.post(url, payload, content_type="application/json")
        assert response.status_code == 401

    def test_generate_playlist_weather_not_found(self, client, user):
        client.force_login(user)
        url = "/api/interactions/playlists/generate/"
        payload = {"count": 10, "weather_id": 99999, "use_context": True}
        response = client.post(url, payload, content_type="application/json")
        assert response.status_code == 404
        assert response.json()["error"] == "Weather context no encontrado"

    @patch(
        "apps.interactions.services.playlist_generation_service.PlaylistGenerationService.generate_playlist"
    )
    def test_generate_playlist_internal_error(self, mock_generate, client, user):
        client.force_login(user)
        mock_generate.side_effect = Exception("Service error")

        url = "/api/interactions/playlists/generate/"
        payload = {"count": 10}
        response = client.post(url, payload, content_type="application/json")
        assert response.status_code == 500
        assert response.json()["error"] == "Error interno generando la playlist"

    @patch("apps.interactions.views.playlist_api.SpotifyMusicService")
    def test_sync_playlist_spotify_failure(self, mock_spotify_class, client, user):
        client.force_login(user)
        mock_spotify = MagicMock()
        mock_spotify_class.return_value = mock_spotify
        # Use a mock for create_playlist which is what PlaylistCreatorService calls
        mock_spotify.create_playlist.return_value = None  # Failure

        track = Track.objects.create(
            spotify_id="t_fail",
            name="Track Fail",
            uri="spotify:track:fail",
            duration_ms=200000,
            track_number=1,
        )
        playlist = Playlist.objects.create(
            user=user, name="Local Playlist", spotify_id="local_123"
        )
        playlist.tracks.add(track)

        url = "/api/interactions/playlists/local_123/sync-spotify/"
        response = client.post(url)
        assert response.status_code == 500

    @patch("apps.interactions.views.playlist_api.SpotifyMusicService")
    def test_sync_playlist_spotify_add_tracks_failure(
        self, mock_spotify_class, client, user
    ):
        client.force_login(user)
        mock_spotify = MagicMock()
        mock_spotify_class.return_value = mock_spotify

        # PlaylistCreatorService calls create_playlist then add_tracks_to_playlist
        mock_spotify.create_playlist.return_value = {
            "id": "sp_123",
            "uri": "spotify:playlist:123",
            "external_urls": {"spotify": "http://sp.com/123"},
        }
        mock_spotify.add_tracks_to_playlist.return_value = (
            False  # Track addition failure
        )

        track = Track.objects.create(
            spotify_id="t1",
            name="Track 1",
            uri="spotify:track:t1",
            track_number=1,
            duration_ms=200000,
        )
        playlist = Playlist.objects.create(
            user=user, name="Local Playlist", spotify_id="local_456"
        )
        playlist.tracks.add(track)

        url = "/api/interactions/playlists/local_456/sync-spotify/"
        response = client.post(url)
        # It still returns 200 because PlaylistCreatorService.create_atomic_playlist
        # returns the playlist even if track addition failed (with a warning)
        assert response.status_code == 200
        assert response.json()["success"] is True
