from unittest.mock import patch

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone

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

        history_score = service._score_track(
            history_track, weather_context, user_history
        )
        context_score = service._score_track(
            context_track, weather_context, user_history
        )

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

        history_score = service._score_track(
            history_track, weather_context, user_history
        )
        context_score = service._score_track(
            context_track, weather_context, user_history
        )

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
                "artists": [{"id": "remote_artist_1", "name": "Remote Artist"}],
                "album": {"id": "remote_album_1", "name": "Remote Album"},
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


@pytest.mark.django_db
class TestPlaylistGenerationSessionLifecycle:
    @staticmethod
    def _build_track():
        album = Album.objects.create(spotify_id="session_album", name="Session Album")
        return Track.objects.create(
            spotify_id="session_track",
            name="Session Track",
            album=album,
            duration_ms=180000,
            explicit=False,
            track_number=1,
            popularity=70,
            uri="spotify:track:session_track",
        )

    def test_record_interaction_creates_session_row(self):
        from apps.interactions.models import InteractionSession

        user = User.objects.create_user("session_user", "session@test.com", "pass12345")
        track = self._build_track()
        service = PlaylistGenerationService()

        service.record_interaction(
            user=user,
            track=track,
            feedback="completed",
            play_duration=120,
            track_duration=180,
            session_id="session_auto_1",
        )

        session = InteractionSession.objects.get(session_id="session_auto_1")
        assert session.user == user
        assert session.is_active is True
        assert session.total_tracks == 1

    @override_settings(SESSION_INACTIVITY_MINUTES=1)
    def test_close_stale_sessions_marks_session_inactive(self):
        from apps.interactions.models import Interaction, InteractionSession

        user = User.objects.create_user(
            "stale_user", "stale@test.com", "pass12345"
        )
        track = self._build_track()
        service = PlaylistGenerationService()

        session = service._ensure_active_session(user=user, session_id="session_stale_1")
        interaction = Interaction.objects.create(
            user=user,
            track=track,
            feedback="completed",
            play_duration=120,
            track_duration=180,
            session_id=session.session_id,
        )

        stale_time = timezone.now() - timedelta(minutes=5)
        Interaction.objects.filter(id=interaction.id).update(started_at=stale_time)

        closed = service.close_stale_sessions(user=user)
        session.refresh_from_db()

        assert closed == 1
        assert session.is_active is False
        assert session.ended_at is not None
