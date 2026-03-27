"""
Tests para la integración completa con Spotify.
Incluye tests para SpotifyMusicService, sync_spotify_tracks, y playlists.
"""

from unittest.mock import MagicMock, patch
import pytest
from django.test import Client
from django.contrib.auth import get_user_model
from allauth.socialaccount.models import SocialAccount, SocialToken
from django.utils import timezone

from apps.music.models import Track, Album, Artist, Playlist
from apps.music.services.spotify_music_service import SpotifyMusicService

User = get_user_model()


@pytest.mark.django_db
class TestSpotifyMusicServiceExtended:
    """Tests para los nuevos métodos de SpotifyMusicService."""

    @pytest.fixture
    def user_with_spotify(self):
        """Crea un usuario conectado a Spotify."""
        user = User.objects.create_user(
            username="spotify_user",
            email="spotify@test.com",
            is_spotify_connected=True
        )
        # Crear social account y token
        account = SocialAccount.objects.create(
            user=user,
            provider="spotify",
            uid="spotify_123"
        )
        SocialToken.objects.create(
            account=account,
            token="test_access_token",
            token_secret="test_refresh_token",
            expires_at=timezone.now() + timezone.timedelta(hours=1),
        )
        return user

    @patch("apps.music.services.spotify_music_service.spotipy.Spotify")
    def test_get_playlist_tracks(self, mock_spotify_class, user_with_spotify):
        """Test obteniendo tracks de una playlist."""
        mock_client = MagicMock()
        mock_spotify_class.return_value = mock_client
        
        mock_client.playlist_tracks.return_value = {
            "items": [
                {
                    "track": {
                        "id": "track_1",
                        "name": "Song 1",
                        "artists": [{"name": "Artist 1"}],
                        "album": {"name": "Album 1", "id": "album_1"},
                        "duration_ms": 180000,
                        "explicit": False,
                        "popularity": 80,
                        "uri": "spotify:track:track_1",
                    }
                }
            ]
        }

        service = SpotifyMusicService(user_with_spotify)
        tracks = service.get_playlist_tracks("playlist_123", limit=50)

        assert len(tracks) == 1
        assert tracks[0]["id"] == "track_1"
        assert tracks[0]["name"] == "Song 1"
        assert tracks[0]["popularity"] == 80

    @patch("apps.music.services.spotify_music_service.spotipy.Spotify")
    def test_get_user_liked_tracks(self, mock_spotify_class, user_with_spotify):
        """Test obteniendo liked songs del usuario."""
        mock_client = MagicMock()
        mock_spotify_class.return_value = mock_client
        
        mock_client.current_user_saved_tracks.return_value = {
            "items": [
                {
                    "track": {
                        "id": "liked_track_1",
                        "name": "Liked Song",
                        "artists": [{"name": "Favorite Artist"}],
                        "album": {"name": "Favorite Album", "id": "album_2"},
                        "duration_ms": 240000,
                        "explicit": True,
                        "popularity": 75,
                        "uri": "spotify:track:liked_track_1",
                    }
                }
            ]
        }

        service = SpotifyMusicService(user_with_spotify)
        tracks = service.get_user_liked_tracks(limit=50)

        assert len(tracks) == 1
        assert tracks[0]["id"] == "liked_track_1"
        assert tracks[0]["explicit"] is True

    @patch("apps.music.services.spotify_music_service.spotipy.Spotify")
    def test_get_top_tracks(self, mock_spotify_class, user_with_spotify):
        """Test obteniendo top tracks del usuario."""
        mock_client = MagicMock()
        mock_spotify_class.return_value = mock_client
        
        mock_client.current_user_top_tracks.return_value = {
            "items": [
                {
                    "id": "top_track_1",
                    "name": "Top Song",
                    "artists": [{"name": "Top Artist"}],
                    "album": {"name": "Top Album", "id": "album_3"},
                    "duration_ms": 200000,
                    "explicit": False,
                    "popularity": 90,
                    "uri": "spotify:track:top_track_1",
                }
            ]
        }

        service = SpotifyMusicService(user_with_spotify)
        tracks = service.get_top_tracks(time_range="medium_term", limit=50)

        assert len(tracks) == 1
        assert tracks[0]["id"] == "top_track_1"
        assert tracks[0]["popularity"] == 90

    @patch("apps.music.services.spotify_music_service.spotipy.Spotify")
    def test_create_playlist(self, mock_spotify_class, user_with_spotify):
        """Test creando una playlist en Spotify."""
        mock_client = MagicMock()
        mock_spotify_class.return_value = mock_client
        
        mock_client.current_user.return_value = {"id": "user_123"}
        mock_client.user_playlist_create.return_value = {
            "id": "new_playlist_123",
            "name": "Test Playlist",
            "uri": "spotify:playlist:new_playlist_123",
            "snapshot_id": "snapshot_123",
            "external_urls": {"spotify": "https://open.spotify.com/playlist/new_playlist_123"},
            "images": [],
        }

        service = SpotifyMusicService(user_with_spotify)
        playlist = service.create_playlist(
            name="Test Playlist",
            description="Test Description",
            public=True
        )

        assert playlist is not None
        assert playlist["id"] == "new_playlist_123"
        assert playlist["name"] == "Test Playlist"
        mock_client.user_playlist_create.assert_called_once()

    @patch("apps.music.services.spotify_music_service.spotipy.Spotify")
    def test_add_tracks_to_playlist(self, mock_spotify_class, user_with_spotify):
        """Test agregando tracks a una playlist."""
        mock_client = MagicMock()
        mock_spotify_class.return_value = mock_client
        
        service = SpotifyMusicService(user_with_spotify)
        track_uris = [
            "spotify:track:1",
            "spotify:track:2",
            "spotify:track:3",
        ]
        
        result = service.add_tracks_to_playlist("playlist_123", track_uris)
        
        assert result is True
        mock_client.playlist_add_items.assert_called_once()

    @patch("apps.music.services.spotify_music_service.spotipy.Spotify")
    def test_get_audio_features(self, mock_spotify_class, user_with_spotify):
        """Test obteniendo audio features."""
        mock_client = MagicMock()
        mock_spotify_class.return_value = mock_client
        
        mock_client.audio_features.return_value = [
            {
                "id": "track_1",
                "danceability": 0.7,
                "energy": 0.8,
                "key": 0,
                "loudness": -5.5,
                "mode": 1,
                "speechiness": 0.05,
                "acousticness": 0.1,
                "instrumentalness": 0.0,
                "liveness": 0.2,
                "valence": 0.6,
                "tempo": 130,
                "time_signature": 4,
            }
        ]

        service = SpotifyMusicService(user_with_spotify)
        features = service.get_audio_features(["track_1"])

        assert "track_1" in features
        assert features["track_1"]["danceability"] == 0.7
        assert features["track_1"]["energy"] == 0.8


@pytest.mark.django_db
class TestPlaylistGenerationWithSpotify:
    """Tests para PlaylistGenerationService con Spotify."""

    @pytest.fixture
    def user_with_spotify(self):
        """Usuario conectado a Spotify."""
        user = User.objects.create_user(
            username="playlist_user",
            email="playlist@test.com",
            is_spotify_connected=True
        )
        account = SocialAccount.objects.create(
            user=user,
            provider="spotify",
            uid="spotify_456"
        )
        SocialToken.objects.create(
            account=account,
            token="test_token",
            token_secret="test_refresh",
            expires_at=timezone.now() + timezone.timedelta(hours=1),
        )
        return user

    @pytest.fixture
    def sample_tracks(self):
        """Crea algunos tracks para testing."""
        artist = Artist.objects.create(name="Test Artist", spotify_id="artist_1")
        album = Album.objects.create(name="Test Album", spotify_id="album_1")
        
        tracks = []
        for i in range(5):
            track = Track.objects.create(
                spotify_id=f"track_{i}",
                name=f"Track {i}",
                album=album,
                duration_ms=180000,
                track_number=i + 1,
                popularity=70,
                uri=f"spotify:track:track_{i}",
            )
            track.artists.add(artist)
            tracks.append(track)
        
        return tracks

    @patch("apps.interactions.services.playlist_generation_service.SpotifyMusicService")
    def test_playlist_sync_to_spotify(self, mock_spotify_service_class, user_with_spotify, sample_tracks):
        """Test sincronizando playlist con Spotify."""
        from apps.interactions.services.playlist_generation_service import (
            PlaylistGenerationService
        )
        
        # Mock del servicio de Spotify
        mock_service = MagicMock()
        mock_spotify_service_class.return_value = mock_service
        mock_service.client = MagicMock()
        mock_service.create_playlist.return_value = {
            "id": "spotify_playlist_123",
            "uri": "spotify:playlist:spotify_playlist_123",
            "external_urls": {"spotify": "https://open.spotify.com/playlist/spotify_playlist_123"},
        }
        mock_service.add_tracks_to_playlist.return_value = True

        # Crear playlist localmente
        playlist = Playlist.objects.create(
            user=user_with_spotify,
            name="Test Playlist Sync",
            is_public=False,
        )
        for track in sample_tracks:
            playlist.tracks.add(track)

        # Sincronizar con Spotify
        service = PlaylistGenerationService()
        result = service._sync_playlist_to_spotify(user_with_spotify, playlist, sample_tracks)

        assert result is not None
        assert result["id"] == "spotify_playlist_123"
        mock_service.create_playlist.assert_called_once()
        mock_service.add_tracks_to_playlist.assert_called_once()


@pytest.mark.django_db
class TestPlaylistAPIEndpoints:
    """Tests para los endpoints de la API."""

    @pytest.fixture
    def client(self):
        return Client()

    @pytest.fixture
    def user_with_spotify(self):
        user = User.objects.create_user(
            username="api_user",
            email="api@test.com",
            password="test123",
            is_spotify_connected=True
        )
        account = SocialAccount.objects.create(
            user=user,
            provider="spotify",
            uid="spotify_789"
        )
        SocialToken.objects.create(
            account=account,
            token="api_token",
            token_secret="api_refresh",
            expires_at=timezone.now() + timezone.timedelta(hours=1),
        )
        return user

    @pytest.fixture
    def sample_playlist(self, user_with_spotify):
        """Crea una playlist de muestra."""
        artist = Artist.objects.create(name="API Artist", spotify_id="artist_api")
        album = Album.objects.create(name="API Album", spotify_id="album_api")
        
        playlist = Playlist.objects.create(
            user=user_with_spotify,
            name="API Test Playlist",
            spotify_id="playlist_api_123",
            is_public=False,
        )
        
        for i in range(3):
            track = Track.objects.create(
                spotify_id=f"api_track_{i}",
                name=f"API Track {i}",
                album=album,
                duration_ms=180000,
                track_number=i + 1,
                uri=f"spotify:track:api_track_{i}",
            )
            track.artists.add(artist)
            playlist.tracks.add(track)
        
        return playlist

    def test_list_user_playlists(self, client, user_with_spotify, sample_playlist):
        """Test listando playlists del usuario."""
        client.force_login(user_with_spotify)
        response = client.get("/api/interactions/playlists/")
        
        assert response.status_code == 200
        data = response.json()
        assert "playlists" in data
        assert len(data["playlists"]) == 1
        assert data["playlists"][0]["playlist_name"] == "API Test Playlist"

    def test_get_playlist_details(self, client, user_with_spotify, sample_playlist):
        """Test obteniendo detalles de una playlist."""
        client.force_login(user_with_spotify)
        response = client.get(f"/api/interactions/playlists/{sample_playlist.spotify_id}/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["playlist_name"] == "API Test Playlist"
        assert data["tracks_count"] == 3

    @patch("apps.interactions.views.playlist_api.SpotifyMusicService")
    def test_sync_playlist_to_spotify_endpoint(self, mock_spotify_service, client, 
                                               user_with_spotify, sample_playlist):
        """Test sincronizando playlist por API."""
        mock_service = MagicMock()
        mock_spotify_service.return_value = mock_service
        mock_service.client = MagicMock()
        mock_service.create_playlist.return_value = {
            "id": "new_spotify_id",
            "uri": "spotify:playlist:new_spotify_id",
            "external_urls": {"spotify": "https://open.spotify.com/playlist/new_spotify_id"},
        }
        mock_service.add_tracks_to_playlist.return_value = True

        client.force_login(user_with_spotify)
        response = client.post(
            f"/api/interactions/playlists/{sample_playlist.spotify_id}/sync-spotify/"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["spotify_id"] == "new_spotify_id"

    @patch("apps.interactions.views.playlist_api.SpotifyMusicService")
    def test_sync_tracks_endpoint(self, mock_spotify_service, client, user_with_spotify):
        """Test sincronizando tracks por API."""
        mock_service = MagicMock()
        mock_spotify_service.return_value = mock_service
        mock_service.client = MagicMock()
        mock_service.get_user_liked_tracks.return_value = [
            {
                "id": "liked_1",
                "name": "Liked Track",
                "artists": ["Artist"],
                "album": "Album",
                "album_id": "album_123",
                "duration_ms": 180000,
                "explicit": False,
                "popularity": 75,
                "preview_url": "",
                "uri": "spotify:track:liked_1",
            }
        ]
        mock_service.get_audio_features.return_value = {}

        client.force_login(user_with_spotify)
        response = client.post(
            "/api/interactions/tracks/sync/",
            {"source": "liked", "limit": 50}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "synced_count" in data
