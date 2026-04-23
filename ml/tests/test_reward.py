"""
Tests para el módulo de Reward.
"""

import pytest

from ml.reward import RewardCalculator


@pytest.fixture
def calculator():
    """Fixture con instancia de RewardCalculator."""
    return RewardCalculator()


class TestRewardCalculator:
    """Tests para la clase RewardCalculator."""

    def test_initialization(self, calculator):
        """Test de inicialización."""
        assert calculator.base_reward == 1.0
        assert calculator.skip_penalty == -1.0
        assert calculator.completion_bonus == 1.0

    def test_feedback_reward_completed(self, calculator):
        """Test de reward para feedback 'completed'."""
        reward = calculator.calculate_reward(user_feedback="completed")
        assert reward > 0

    def test_feedback_reward_skip(self, calculator):
        """Test de reward para feedback 'skip'."""
        reward = calculator.calculate_reward(user_feedback="skip")
        # base_reward (1.0) + skip_penalty (-1.0) = 0.0
        assert reward <= 0

    def test_feedback_reward_skip_immediate(self, calculator):
        """Test de reward para skip inmediato."""
        reward = calculator.calculate_reward(user_feedback="skip_immediate")
        # base_reward (1.0) + skip_penalty * 1.5 (-1.5) = -0.5
        assert reward <= 0

    def test_weather_context_reward(self, calculator):
        """Test de reward con contexto climático."""
        weather = {"temperature": 22, "humidity": 60, "main_status": "clear"}
        reward = calculator.calculate_reward(
            user_feedback="completed", weather_context=weather
        )
        assert reward > 1.0

    def test_audio_features_reward(self, calculator):
        """Test de reward con características de audio."""
        audio = {"energy": 0.8, "danceability": 0.7, "valence": 0.6}
        reward = calculator.calculate_reward(
            user_feedback="completed", track_audio_features=audio
        )
        assert reward > 0

    def test_user_history_consistency(self, calculator):
        """Test de consistencia con historico del usuario."""
        audio = {"energy": 0.5, "danceability": 0.5, "valence": 0.5}
        history = {
            "avg_energy": 0.5,
            "avg_danceability": 0.5,
            "avg_valence": 0.5,
            "skip_rate": 0.3,
        }
        reward = calculator.calculate_reward(
            user_feedback="completed",
            track_audio_features=audio,
            user_history=history,
        )
        assert reward > 0

    def test_normalize_reward(self, calculator):
        """Test de normalización de reward."""
        raw_reward = 5.0
        normalized = calculator.normalize_reward(raw_reward, min_val=-2.0, max_val=2.0)
        assert normalized == 2.0
        assert -2.0 <= normalized <= 2.0

    def test_all_factors_combined(self, calculator):
        """Test con todos los factores combinados."""
        reward = calculator.calculate_reward(
            user_feedback="completed",
            weather_context={"temperature": 25, "humidity": 50, "main_status": "sunny"},
            track_audio_features={"energy": 0.8, "danceability": 0.75, "valence": 0.7},
            user_history={
                "avg_energy": 0.75,
                "avg_danceability": 0.7,
                "skip_rate": 0.2,
            },
        )
        assert isinstance(reward, float)
        # El reward puede oscilar entre -2.0 (skip inmediato + contexto negativo) y 3.0+ (todos positivos)
        assert reward >= -2.0
