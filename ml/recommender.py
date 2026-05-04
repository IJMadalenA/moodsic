"""
Module for ML-based track recommendation.

Builds a feature matrix from track audio features and lyrics sentiment,
fits a NearestNeighbors model, and scores tracks against a target mood vector.
Falls back to a heuristic scoring function when the model is not fitted.
"""

import logging

import numpy as np
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

_ml_recommender_instance = None


def get_ml_recommender():
    """
    Obtains or creates the global MLRecommender singleton instance.

    Returns:
        MLRecommender: The global recommender instance.
    """
    global _ml_recommender_instance
    if _ml_recommender_instance is None:
        _ml_recommender_instance = MLRecommender()
    return _ml_recommender_instance


class MLRecommender:
    """
    Recommends tracks using NearestNeighbors on audio features and lyrics sentiment.

    Builds a normalized feature matrix from track audio features and optional
    lyrics sentiment scores, fits a cosine-similarity NearestNeighbors model,
    and scores tracks against a user-defined target mood vector. When the model
    has not been fitted, falls back to a heuristic scoring function.
    """

    def __init__(self, n_neighbors=100):
        """
        Initializes the recommender with a NearestNeighbors model and scaler.

        Args:
            n_neighbors: Number of neighbors to consider in the k-NN search.
        """
        self.model = NearestNeighbors(n_neighbors=n_neighbors, metric="cosine")
        self.scaler = StandardScaler()
        self._fitted: bool = False
        self.feature_matrix_: np.ndarray | None = None
        self._valid_indices_: list[int] = []

    def _build_feature_matrix(self, tracks):
        """
        Builds a normalized feature matrix from a list of tracks.

        Extracts audio features and optional lyrics sentiment for each track,
        normalizing all values to the [0, 1] range. Tracks without audio
        features are skipped.

        Args:
            tracks: List of Track instances.

        Returns:
            Tuple of (np.ndarray | None, list[int]): Feature matrix with shape
            (n_valid_tracks, 13) and the list of original track indices that
            were included. Returns (None, []) when no tracks have audio features.
        """
        rows = []
        valid_indices = []

        for idx, track in enumerate(tracks):
            try:
                af = track.audio_features
            except Exception as e:
                logger.debug("Error extracting features for track %s: %s", track.spotify_id, e)
                continue

            if af is None:
                continue

            sentiment = 0.5
            try:
                lyrics = track.lyrics.first()
                if lyrics is not None and lyrics.sentiment_score is not None:
                    sentiment = (lyrics.sentiment_score + 1.0) / 2.0
            except Exception as e:
                logger.debug("Error getting lyrics for track %s: %s", track.spotify_id, e)
                sentiment = 0.5

            row = [
                af.danceability,
                af.energy,
                af.key / 11.0,
                (af.loudness + 60.0) / 60.0,
                float(af.mode),
                af.speechiness,
                af.acousticness,
                af.instrumentalness,
                af.liveness,
                af.valence,
                (af.tempo - 40.0) / 160.0,
                (af.time_signature - 1.0) / 4.0,
                sentiment,
            ]
            rows.append(row)
            valid_indices.append(idx)

        if not rows:
            return None, []

        matrix = np.array(rows, dtype=np.float64)
        return matrix, valid_indices

    def fit(self, tracks):
        """
        Fits the NearestNeighbors model on the given tracks.

        Builds the feature matrix, scales it, and fits the k-NN model.
        If no valid tracks have audio features, the model remains unfitted.

        Args:
            tracks: List of Track instances to fit on.

        Returns:
            MLRecommender: Self, for method chaining.
        """
        matrix, valid_indices = self._build_feature_matrix(tracks)
        if matrix is None:
            self._fitted = False
            self.feature_matrix_ = None
            self._valid_indices_ = []
            return self

        self.scaler.fit(matrix)
        scaled = self.scaler.transform(matrix)
        self.model.fit(scaled)
        self.feature_matrix_ = matrix
        self._valid_indices_ = valid_indices
        self._fitted = True
        return self

    def build_target_vector(self, target_mood=None, news_sentiment=0.0):
        """
        Builds a 13-dimensional target feature vector for scoring.

        Combines a user-provided target mood dictionary with sensible defaults
        and appends a normalized news sentiment value.

        Args:
            target_mood: Dict with optional target_* keys (danceability, energy,
                valence, etc.). Missing keys fall back to defaults.
            news_sentiment: News sentiment score in [-1, 1], mapped to [0, 1].

        Returns:
            np.ndarray: Target vector of shape (13,).
        """
        if target_mood is None:
            target_mood = {}

        defaults = {
            "target_danceability": 0.5,
            "target_energy": 0.5,
            "target_key": 0.5,
            "target_loudness": 0.58,
            "target_mode": 1.0,
            "target_speechiness": 0.1,
            "target_acousticness": 0.3,
            "target_instrumentalness": 0.0,
            "target_liveness": 0.2,
            "target_valence": 0.5,
            "target_tempo": 0.5,
            "target_time_signature": 0.75,
        }

        vec = np.array([
            target_mood.get("target_danceability", defaults["target_danceability"]),
            target_mood.get("target_energy", defaults["target_energy"]),
            target_mood.get("target_key", defaults["target_key"]),
            target_mood.get("target_loudness", defaults["target_loudness"]),
            target_mood.get("target_mode", defaults["target_mode"]),
            target_mood.get("target_speechiness", defaults["target_speechiness"]),
            target_mood.get("target_acousticness", defaults["target_acousticness"]),
            target_mood.get("target_instrumentalness", defaults["target_instrumentalness"]),
            target_mood.get("target_liveness", defaults["target_liveness"]),
            target_mood.get("target_valence", defaults["target_valence"]),
            target_mood.get("target_tempo", defaults["target_tempo"]),
            target_mood.get("target_time_signature", defaults["target_time_signature"]),
            (news_sentiment + 1.0) / 2.0,
        ], dtype=np.float64)

        return vec

    def score_tracks(self, tracks, target_mood=None, news_sentiment=0.0, top_k=None):
        """
        Scores tracks by similarity to the target mood vector.

        When the model is fitted, uses NearestNeighbors cosine similarity.
        When not fitted, falls back to heuristic scoring.

        Args:
            tracks: List of Track instances to score.
            target_mood: Dict with optional target_* keys for audio feature
                preferences. Defaults to neutral values if not provided.
            news_sentiment: News sentiment score in [-1, 1].
            top_k: If provided, returns only the top-k scored tracks.

        Returns:
            list[tuple[int, float]]: List of (track_index, score) sorted
            descending by score.
        """
        if not tracks:
            return []

        if not self._fitted:
            return self._heuristic_score(tracks, top_k)

        target_vec = self.build_target_vector(target_mood, news_sentiment)
        target_scaled = self.scaler.transform(target_vec.reshape(1, -1))

        n_samples = self.feature_matrix_.shape[0]
        n_neighbors = min(self.model.n_neighbors, n_samples)
        distances, indices = self.model.kneighbors(
            target_scaled, n_neighbors=n_neighbors, return_distance=True
        )
        similarities = 1.0 - distances[0]

        result = []
        for nn_rank in range(len(similarities)):
            neighbor_idx = indices[0][nn_rank]
            track_original_idx = self._valid_indices_[neighbor_idx]
            sim = similarities[nn_rank]
            result.append((track_original_idx, float(sim)))

        result.sort(key=lambda x: x[1], reverse=True)

        if top_k is not None:
            result = result[:top_k]

        return result

    def _heuristic_score(self, tracks, top_k=None):
        """
        Scores tracks using a fixed-weight heuristic function.

        Unlike the ML path which uses the target_mood vector, this heuristic
        uses fixed weights for valence (0.3), energy (0.25), danceability (0.25),
        and popularity (0.2). It does not consider user-specified target
        preferences. This is intentional for graceful degradation when the
        k-NN model has not been fitted.

        Args:
            tracks: List of Track instances to score.
            top_k: If provided, returns only the top-k scored tracks.

        Returns:
            list[tuple[int, float]]: List of (track_index, score) sorted
            descending by score, with scores clamped to [0.0, 1.0].
        """
        if not tracks:
            return []

        scores = []
        for idx, track in enumerate(tracks):
            try:
                af = track.audio_features
            except Exception:
                scores.append((idx, 0.0))
                continue

            if af is None:
                scores.append((idx, 0.0))
                continue

            popularity = float(getattr(track, "popularity", 0) or 0)
            score = (
                float(af.valence) * 0.3
                + float(af.energy) * 0.25
                + float(af.danceability) * 0.25
                + (popularity / 100.0) * 0.2
            )
            scores.append((idx, min(max(score, 0.0), 1.0)))

        scores.sort(key=lambda x: x[1], reverse=True)

        if top_k is not None:
            scores = scores[:top_k]

        return scores
