from unittest.mock import MagicMock, patch

import pytest

from apps.music.services.spotify_music_service import SpotifyMusicService
from apps.users.models.user import User


@pytest.mark.django_db
class TestSpotifyServiceExtended:
    @pytest.fixture
    def user(self):
        return User.objects.create_user(
            username="spotify_ext", email="spotify_ext@test.com"
        )

    @pytest.fixture
    def service(self, user):
        return SpotifyMusicService(user)

    @patch("spotipy.Spotify")
    def test_get_user_info(self, mock_spotify, service):
        mock_instance = MagicMock()
        mock_spotify.return_value = mock_instance
        service.client = mock_instance

        mock_instance.current_user.return_value = {"id": "user1"}
        info = service.get_user_info()
        assert info["id"] == "user1"

    @patch("spotipy.Spotify")
    def test_search_tracks(self, mock_spotify, service):
        mock_instance = MagicMock()
        mock_spotify.return_value = mock_instance
        service.client = mock_instance

        mock_instance.search.return_value = {"tracks": {"items": []}}
        results = service.search_tracks("query")
        assert "tracks" in results

    @patch("spotipy.Spotify")
    def test_get_recommendations(self, mock_spotify, service):
        mock_instance = MagicMock()
        mock_spotify.return_value = mock_instance
        service.client = mock_instance

        mock_instance.recommendations.return_value = {"tracks": []}
        results = service.get_recommendations(seed_genres=["rock"])
        assert "tracks" in results

    @patch("spotipy.Spotify")
    def test_get_playlist_tracks(self, mock_spotify, service):
        mock_instance = MagicMock()
        mock_spotify.return_value = mock_instance
        service.client = mock_instance

        mock_instance.playlist_tracks.return_value = {
            "items": [{"track": {"id": "t1", "name": "T1"}}]
        }
        tracks = service.get_playlist_tracks("spotify:playlist:123")
        assert len(tracks) == 1
        assert tracks[0]["name"] == "T1"

    @patch("spotipy.Spotify")
    def test_get_user_liked_tracks(self, mock_spotify, service):
        mock_instance = MagicMock()
        mock_spotify.return_value = mock_instance
        service.client = mock_instance

        mock_instance.current_user_saved_tracks.return_value = {
            "items": [{"track": {"id": "t1"}}]
        }
        tracks = service.get_user_liked_tracks()
        assert len(tracks) == 1

    @patch("spotipy.Spotify")
    def test_get_top_tracks(self, mock_spotify, service):
        mock_instance = MagicMock()
        mock_spotify.return_value = mock_instance
        service.client = mock_instance

        mock_instance.current_user_top_tracks.return_value = {"items": [{"id": "t1"}]}
        tracks = service.get_top_tracks()
        assert len(tracks) == 1

    @patch("spotipy.Spotify")
    def test_get_audio_features(self, mock_spotify, service):
        mock_instance = MagicMock()
        mock_spotify.return_value = mock_instance
        service.client = mock_instance

        mock_instance.audio_features.return_value = [{"id": "t1", "energy": 0.5}]
        features = service.get_audio_features(["t1"])
        assert "t1" in features

    def test_no_client_methods(self, user):
        service = SpotifyMusicService(user)
        service.client = None

        assert service.get_user_info() is None
        assert service.search_tracks("q") is None
        assert service.get_recommendations() is None
        assert service.create_playlist("n") is None
        assert service.add_tracks_to_playlist("id", ["uri"]) is None
        assert service.get_playlist_tracks("id") == []
        assert service.get_user_liked_tracks() == []
        assert service.get_top_tracks() == []
        assert service.get_audio_features(["id"]) == {}
