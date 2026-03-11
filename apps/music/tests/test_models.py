import pytest
from django.contrib.auth import get_user_model

from apps.music.models import Album, Artist, Playlist, Track, TrackAudioFeatures

User = get_user_model()


@pytest.mark.django_db
class TestMusicModels:
    def test_artist_creation(self):
        artist = Artist.objects.create(
            spotify_id="artist_123", name="Test Artist", genres=["rock", "pop"]
        )
        assert artist.name == "Test Artist"
        assert str(artist) == "Test Artist"
        assert Artist.objects.count() == 1

    def test_album_creation(self):
        artist = Artist.objects.create(spotify_id="artist_123", name="Artist")
        album = Album.objects.create(
            spotify_id="album_123", name="Test Album", release_date="2024"
        )
        album.artists.add(artist)
        assert album.name == "Test Album"
        assert album.artists.count() == 1
        assert str(album) == "Test Album"

    def test_track_creation(self):
        artist = Artist.objects.create(spotify_id="artist_123", name="Artist")
        album = Album.objects.create(spotify_id="album_123", name="Album")
        track = Track.objects.create(
            spotify_id="track_123",
            name="Test Track",
            album=album,
            duration_ms=200000,
            track_number=1,
        )
        track.artists.add(artist)
        assert track.name == "Test Track"
        assert track.album == album
        assert track.artists.count() == 1
        assert "Test Track" in str(track)

    def test_audio_features_creation(self):
        track = Track.objects.create(
            spotify_id="track_123",
            name="Test Track",
            duration_ms=200000,
            track_number=1,
        )
        features = TrackAudioFeatures.objects.create(
            track=track,
            danceability=0.8,
            energy=0.7,
            key=5,
            loudness=-5.0,
            mode=1,
            speechiness=0.05,
            acousticness=0.1,
            instrumentalness=0.0,
            liveness=0.1,
            valence=0.6,
            tempo=120.0,
            time_signature=4,
        )
        assert features.track == track
        assert features.danceability == 0.8
        assert str(features) == f"Features for {track.name}"

    def test_playlist_creation(self):
        user = User.objects.create_user(username="testuser", password="password")
        track = Track.objects.create(
            spotify_id="track_123",
            name="Test Track",
            duration_ms=200000,
            track_number=1,
        )
        playlist = Playlist.objects.create(
            spotify_id="playlist_123", user=user, name="My Playlist"
        )
        playlist.tracks.add(track, through_defaults={"order": 1})

        assert playlist.name == "My Playlist"
        assert playlist.user == user
        assert playlist.tracks.count() == 1
        assert str(playlist) == f"My Playlist ({user.username})"
