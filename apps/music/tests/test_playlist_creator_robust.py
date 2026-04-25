from unittest.mock import MagicMock

import pytest

from apps.music.services.playlist_creator_service import PlaylistCreatorService


@pytest.mark.django_db
class TestPlaylistCreatorRobust:
    @pytest.fixture
    def mock_spotify(self):
        return MagicMock()

    @pytest.fixture
    def service(self, mock_spotify):
        return PlaylistCreatorService(mock_spotify)

    def test_create_atomic_playlist_success(self, service, mock_spotify):
        mock_spotify.create_playlist.return_value = {"id": "p1"}
        mock_spotify.add_tracks_to_playlist.return_value = True

        res = service.create_atomic_playlist("Name", "Desc", ["uri1"])
        assert res["id"] == "p1"
        assert mock_spotify.add_tracks_to_playlist.called

    def test_create_atomic_playlist_fail_base(self, service, mock_spotify):
        mock_spotify.create_playlist.return_value = None
        res = service.create_atomic_playlist("Name", "Desc", ["uri1"])
        assert res is None

    def test_generate_from_recommendations(self, service, mock_spotify):
        mock_spotify.get_recommendations.return_value = [{"uri": "u1"}, {"uri": "u2"}]
        mock_spotify.create_playlist.return_value = {"id": "p1"}

        res = service.generate_from_recommendations("Rec", seed_genres=["rock"])
        assert res["id"] == "p1"
        assert mock_spotify.get_recommendations.called

    def test_get_playlist_details_with_stats(self, service, mock_spotify):
        mock_spotify.get_playlist_stats.return_value = {"name": "P1"}
        res = service.get_playlist_details_with_stats("p1")
        assert res["name"] == "P1"
