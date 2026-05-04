import numpy as np
import pytest
from sklearn.neighbors import NearestNeighbors

from apps.music.models import Track, TrackAudioFeatures, TrackLyrics
from ml.recommender import MLRecommender


@pytest.mark.django_db
class TestMLRecommender:
    @pytest.fixture
    def tracks_with_audio(self):
        features = [
            (0.8, 0.9, 5, -4.0, 1, 0.05, 0.1, 0.0, 0.1, 0.85, 120.0, 4),
            (0.2, 0.1, 0, -20.0, 0, 0.03, 0.95, 0.05, 0.15, 0.1, 80.0, 3),
            (0.6, 0.5, 2, -8.0, 1, 0.1, 0.3, 0.0, 0.2, 0.5, 100.0, 4),
        ]
        tracks = []
        for i, feat in enumerate(features):
            t = Track.objects.create(
                spotify_id=f"rm{i}",
                name=f"Track {i}",
                duration_ms=200000,
                track_number=1,
            )
            TrackAudioFeatures.objects.create(
                track=t,
                danceability=feat[0],
                energy=feat[1],
                key=feat[2],
                loudness=feat[3],
                mode=feat[4],
                speechiness=feat[5],
                acousticness=feat[6],
                instrumentalness=feat[7],
                liveness=feat[8],
                valence=feat[9],
                tempo=feat[10],
                time_signature=feat[11],
            )
            tracks.append(t)
        return tracks

    @pytest.fixture
    def tracks_with_lyrics(self, tracks_with_audio):
        TrackLyrics.objects.create(
            track=tracks_with_audio[0],
            artist_name="X",
            song_name="Happy",
            text="joy joy joy",
            match_status="matched",
            sentiment_score=0.8,
            sentiment_label="positive",
            sentiment_pos=0.7,
            sentiment_neg=0.0,
            sentiment_neu=0.3,
        )
        TrackLyrics.objects.create(
            track=tracks_with_audio[1],
            artist_name="Y",
            song_name="Sad",
            text="sad sad sad",
            match_status="matched",
            sentiment_score=-0.7,
            sentiment_label="negative",
            sentiment_pos=0.0,
            sentiment_neg=0.6,
            sentiment_neu=0.4,
        )
        return tracks_with_audio

    def test_initialization(self):
        recommender = MLRecommender()
        assert recommender.model is not None
        assert recommender.scaler is not None
        assert isinstance(recommender.model, NearestNeighbors)

    def test_build_feature_matrix_no_features(self):
        recommender = MLRecommender()
        t = Track.objects.create(
            spotify_id="no_feat",
            name="No Features",
            duration_ms=1000,
            track_number=1,
        )
        tracks = [t]
        matrix, valid_indices = recommender._build_feature_matrix(tracks)
        assert matrix is None
        assert valid_indices == []

    def test_build_feature_matrix_with_features(self, tracks_with_audio):
        recommender = MLRecommender()
        matrix, valid_indices = recommender._build_feature_matrix(tracks_with_audio)
        assert matrix is not None
        assert matrix.shape == (3, 13)
        assert valid_indices == [0, 1, 2]
        assert 0.0 <= matrix.min() <= matrix.max() <= 1.0

    def test_fit(self, tracks_with_audio):
        recommender = MLRecommender()
        recommender.fit(tracks_with_audio)
        assert recommender._fitted
        assert recommender.feature_matrix_ is not None

    def test_score_tracks_returns_correct_order(self, tracks_with_audio):
        recommender = MLRecommender()
        recommender.fit(tracks_with_audio)

        target = {
            "target_danceability": 0.8,
            "target_energy": 0.9,
            "target_valence": 0.85,
        }
        scored = recommender.score_tracks(tracks_with_audio, target_mood=target)

        assert len(scored) == 3
        assert scored[0][1] >= scored[1][1] >= scored[2][1]
        assert scored[0][1] >= scored[-1][1]

    def test_score_tracks_not_fitted_returns_heuristic(self, tracks_with_audio):
        recommender = MLRecommender()
        scored = recommender.score_tracks(tracks_with_audio)
        assert len(scored) == 3
        for _idx, s in scored:
            assert 0.0 <= s <= 1.0

    def test_score_tracks_with_lyrics_sentiment(self, tracks_with_lyrics):
        recommender = MLRecommender()
        recommender.fit(tracks_with_lyrics)

        target = {
            "target_danceability": 0.5,
            "target_energy": 0.5,
            "target_valence": 0.9,
            "target_acousticness": 0.5,
        }
        scored = recommender.score_tracks(tracks_with_lyrics, target_mood=target)
        assert scored[0][1] > scored[-1][1]

    def test_build_target_vector(self):
        recommender = MLRecommender()
        target_mood = {
            "target_danceability": 0.7,
            "target_energy": 0.4,
            "target_valence": 0.5,
        }
        vec = recommender.build_target_vector(target_mood, news_sentiment=0.3)
        assert len(vec) == 13
        assert 0.0 <= vec[0] <= 1.0
        assert 0.0 <= vec[1] <= 1.0
        assert 0.0 <= vec[9] <= 1.0
        assert 0.5 <= vec[-1] <= 1.0

    def test_build_target_vector_defaults(self):
        recommender = MLRecommender()
        vec = recommender.build_target_vector()
        assert len(vec) == 13
        assert vec[-1] == 0.5

    def test_empty_tracks_returns_empty(self):
        recommender = MLRecommender()
        scored = recommender.score_tracks([])
        assert scored == []

    def test_fallback_without_features(self):
        recommender = MLRecommender()
        t = Track.objects.create(
            spotify_id="nof",
            name="No F",
            duration_ms=1000,
            track_number=1,
        )
        scored = recommender.score_tracks([t])
        assert len(scored) == 1
        assert 0.0 <= scored[0][1] <= 1.0
