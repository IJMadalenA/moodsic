import pytest
from django.contrib.auth import get_user_model

from apps.music.models import Playlist, PlaylistGenre

User = get_user_model()


@pytest.mark.django_db
class TestPlaylistGenreModel:
    def test_create_playlistgenre(self):
        user = User.objects.create_user(username="pguser", password="pass")
        playlist = Playlist.objects.create(
            spotify_id="pl_123", user=user, name="Test Playlist"
        )
        genre = PlaylistGenre.objects.create(
            playlist=playlist, genre="rock", subgenre="indie"
        )
        assert genre.genre == "rock"
        assert str(genre) == "Test Playlist \u2192 rock"
        assert playlist.genres.count() == 1

    def test_unique_together(self):
        user = User.objects.create_user(username="pguser2", password="pass")
        playlist = Playlist.objects.create(
            spotify_id="pl_456", user=user, name="P2"
        )
        PlaylistGenre.objects.create(playlist=playlist, genre="pop")
        with pytest.raises(Exception):
            PlaylistGenre.objects.create(playlist=playlist, genre="pop")

    def test_playlist_null_user(self):
        playlist = Playlist.objects.create(spotify_id="sys_pl", name="System Playlist")
        assert playlist.user is None
        assert str(playlist) == "System Playlist (system)"
