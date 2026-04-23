"""
Tests para el módulo State Builder.
"""

import numpy as np
import pytest

from ml.state_builder import StateBuilder, get_state_builder


@pytest.fixture
def builder():
    """Fixture con instancia de StateBuilder."""
    return StateBuilder()


@pytest.fixture
def mock_user(db):
    """Fixture con usuario mock."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    return User.objects.create_user(username="testuser", email="test@test.com")


class TestStateBuilder:
    """Tests para la clase StateBuilder."""

    def test_initialization(self, builder):
        """Test de inicialización."""
        assert builder.state_dim == 45
        assert builder.weather_features == 10
        assert builder.audio_features_dim == 12
        assert builder.user_history_dim == 8

    def test_build_state_basic(self, builder, mock_user):
        """Test de construcción básica de estado."""
        state = builder.build_state(mock_user)

        assert isinstance(state, np.ndarray)
        assert state.shape == (45,)
        assert state.dtype == np.float32
        assert np.all((state >= 0) & (state <= 1))

    def test_build_state_with_weather(self, builder, mock_user):
        """Test de construcción de estado con contexto climático."""
        weather = {
            "temperature": 22,
            "humidity": 60,
            "wind_speed": 5,
            "main_status": "clear",
        }
        state = builder.build_state(mock_user, weather_context=weather)

        assert state.shape == (45,)
        assert np.all((state >= 0) & (state <= 1))

    def test_build_state_with_track(self, builder, mock_user):
        """Test de construcción de estado con características de track."""
        track = {
            "energy": 0.8,
            "danceability": 0.7,
            "valence": 0.6,
            "tempo": 120,
        }
        state = builder.build_state(mock_user, current_track=track)

        assert state.shape == (45,)

    def test_normalize_weather_features(self, builder):
        """Test de normalización de features de clima."""
        state = builder._extract_weather_features(
            {
                "temperature": 25,
                "humidity": 70,
                "wind_speed": 10,
                "main_status": "rain",
            }
        )

        assert state.shape == (10,)
        assert np.all((state >= 0) & (state <= 1))

    def test_normalize_audio_features(self, builder):
        """Test de normalización de features de audio."""
        audio = {
            "energy": 0.7,
            "danceability": 0.8,
            "valence": 0.5,
            "tempo": 140,
        }
        state = builder._extract_audio_features(audio)

        assert state.shape == (12,)
        assert np.all((state >= 0) & (state <= 1))

    def test_extract_user_history(self, builder, mock_user):
        """Test de extracción de historico del usuario."""
        state = builder._extract_user_history_features(mock_user)

        assert state.shape == (8,)
        assert np.all((state >= 0) & (state <= 1))

    def test_extract_context_features(self, builder):
        """Test de extracción de features contextuales."""
        state = builder._extract_context_features("morning")

        assert state.shape == (15,)
        assert np.all((state >= 0) & (state <= 1))

    def test_normalize_function(self, builder):
        """Test de función de normalización."""
        # Temperatura
        normalized = builder._normalize(25, {"min_val": -50, "max_val": 50})
        assert 0 < normalized < 1

        # Fuera de rango
        normalized = builder._normalize(60, {"min_val": -50, "max_val": 50})
        assert normalized == 1.0

    def test_time_of_day_encoding(self):
        """Test de encoding de hora del día."""
        morning = StateBuilder._encode_time_of_day("morning")
        assert morning == [1.0, 0.0, 0.0, 0.0]

        evening = StateBuilder._encode_time_of_day("evening")
        assert evening == [0.0, 0.0, 1.0, 0.0]

    def test_season_encoding(self):
        """Test de encoding de estación."""
        winter = StateBuilder._encode_season("winter")
        assert winter == [1.0, 0.0, 0.0, 0.0]

        summer = StateBuilder._encode_season("summer")
        assert summer == [0.0, 0.0, 1.0, 0.0]

    def test_singleton_pattern(self):
        """Test del patrón singleton."""
        builder1 = get_state_builder()
        builder2 = get_state_builder()

        assert builder1 is builder2
