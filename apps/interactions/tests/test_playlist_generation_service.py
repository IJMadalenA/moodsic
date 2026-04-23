from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings

from apps.interactions.services.playlist_generation_service import (
    PlaylistGenerationService,
)
from apps.music.models import Album, Artist, Track, TrackAudioFeatures

User = get_user_model()


@pytest.mark.django_db
class TestPlaylistGenerationServiceScoring:
    def _build_tracks(self):
        album = Album.objects.create(spotify_id="album_scoring", name="Album Scoring")

        favorite_artist = Artist.objects.create(
            spotify_id="artist_favorite",
            name="Favorite Artist",
            genres=["jazz"],
        )
        context_artist = Artist.objects.create(
            spotify_id="artist_context",
            name="Context Artist",
            genres=["dance"],
        )

        history_track = Track.objects.create(
            spotify_id="track_history",
            name="History Track",
            album=album,
            duration_ms=180000,
            explicit=False,
            track_number=1,
            popularity=35,
            uri="spotify:track:history",
        )
        history_track.artists.add(favorite_artist)
        TrackAudioFeatures.objects.create(
            track=history_track,
            danceability=0.25,
            energy=0.20,
            key=0,
            loudness=-10,
            mode=1,
            speechiness=0.05,
            acousticness=0.75,
            instrumentalness=0.1,
            liveness=0.2,
            valence=0.20,
            tempo=95,
            time_signature=4,
        )

        context_track = Track.objects.create(
            spotify_id="track_context",
            name="Context Track",
            album=album,
            duration_ms=180000,
            explicit=False,
            track_number=2,
            popularity=90,
            uri="spotify:track:context",
        )
        context_track.artists.add(context_artist)
        TrackAudioFeatures.objects.create(
            track=context_track,
            danceability=0.90,
            energy=0.92,
            key=0,
            loudness=-4,
            mode=1,
            speechiness=0.04,
            acousticness=0.08,
            instrumentalness=0.0,
            liveness=0.2,
            valence=0.88,
            tempo=128,
            time_signature=4,
        )

        return history_track, context_track

    @override_settings(RECOMMENDER_CONTEXT_WEIGHT=1.0, RECOMMENDER_HISTORY_WEIGHT=0.0)
    def test_context_heavy_scoring_prioritizes_context_fit(self):
        service = PlaylistGenerationService()
        history_track, context_track = self._build_tracks()

        user_history = {
            "favorite_artists": ["Favorite Artist"],
            "favorite_genres": ["jazz"],
            "avg_energy": 0.2,
            "avg_danceability": 0.25,
            "avg_valence": 0.2,
        }
        weather_context = {
            "main_status": "Clear",
            "description": "sunny sky",
            "temperature": 28,
        }

        history_score = service._score_track(history_track, weather_context, user_history)
        context_score = service._score_track(context_track, weather_context, user_history)

        assert context_score > history_score

    @override_settings(RECOMMENDER_CONTEXT_WEIGHT=0.0, RECOMMENDER_HISTORY_WEIGHT=1.0)
    def test_history_heavy_scoring_prioritizes_user_favorites(self):
        service = PlaylistGenerationService()
        history_track, context_track = self._build_tracks()

        user_history = {
            "favorite_artists": ["Favorite Artist"],
            "favorite_genres": ["jazz"],
            "avg_energy": 0.2,
            "avg_danceability": 0.25,
            "avg_valence": 0.2,
        }
        weather_context = {
            "main_status": "Clear",
            "description": "sunny sky",
            "temperature": 28,
        }

        history_score = service._score_track(history_track, weather_context, user_history)
        context_score = service._score_track(context_track, weather_context, user_history)

        assert history_score > context_score

    @patch("apps.interactions.services.playlist_generation_service.SpotifyMusicService")
    def test_available_tracks_fall_back_to_spotify_when_local_catalog_is_empty(
        self, mock_spotify_service
    ):
        user = User.objects.create_user(
            "spotify_fallback_user",
            "spotify-fallback@example.com",
            "pass12345",
            is_spotify_connected=True,
        )
        service = PlaylistGenerationService()

        mock_instance = mock_spotify_service.return_value
        mock_instance.client = object()
        mock_instance.get_user_liked_tracks.return_value = [
            {
                "id": "remote_track_1",
                "name": "Remote Track 1",
                "artists": ["Remote Artist"],
                "album": "Remote Album",
                "album_id": "remote_album_1",
                "duration_ms": 200000,
                "explicit": False,
                "popularity": 77,
                "uri": "spotify:track:remote_track_1",
                "preview_url": "",
            }
        ]
        mock_instance.get_top_tracks.return_value = []

        tracks = service._get_available_tracks(user, limit=20)

        assert len(tracks) == 1
        assert tracks[0].spotify_id == "remote_track_1"
        assert Track.objects.filter(spotify_id="remote_track_1").exists()
