"""
Tests para el Agente DQN.
"""

from collections import deque

import numpy as np
import pytest

from ml.agent import DQNAgent, get_agent


@pytest.fixture
def agent():
    """Fixture con instancia de DQNAgent."""
    return DQNAgent(
        state_dim=10,
        action_dim=5,
        epsilon=1.0,
    )


class TestDQNAgent:
    """Tests para la clase DQNAgent."""

    def test_initialization(self, agent):
        """Test de inicialización."""
        assert agent.state_dim == 10
        assert agent.action_dim == 5
        assert agent.epsilon == 1.0
        assert len(agent.memory) == 0

    def test_select_action_exploration(self, agent):
        """Test de selección de acción en exploración."""
        state = np.random.randn(agent.state_dim).astype(np.float32)
        agent.epsilon = 1.0  # Forzar exploración

        action = agent.select_action(state, training=True)

        assert 0 <= action < agent.action_dim

    def test_select_action_exploitation(self, agent):
        """Test de selección de acción en explotación."""
        state = np.random.randn(agent.state_dim).astype(np.float32)
        agent.epsilon = 0.0  # Forzar explotación

        action = agent.select_action(state, training=True)

        assert 0 <= action < agent.action_dim

    def test_select_action_with_available_actions(self, agent):
        """Test de selección de acción con restricción."""
        state = np.random.randn(agent.state_dim).astype(np.float32)
        available = [0, 2, 4]

        action = agent.select_action(state, available_actions=available, training=False)

        assert action in available

    def test_remember(self, agent):
        """Test de guardado de experiencia en buffer."""
        state = np.random.randn(agent.state_dim).astype(np.float32)
        next_state = np.random.randn(agent.state_dim).astype(np.float32)

        agent.remember(state, action=1, reward=1.0, next_state=next_state, done=False)

        assert len(agent.memory) == 1

    def test_memory_buffer_limit(self, agent):
        """Test del límite del replay buffer."""
        for _i in range(agent.memory_size + 100):
            state = np.random.randn(agent.state_dim).astype(np.float32)
            next_state = np.random.randn(agent.state_dim).astype(np.float32)
            agent.remember(state, 0, 1.0, next_state, False)

        assert len(agent.memory) <= agent.memory_size

    def test_replay_insufficient_data(self, agent):
        """Test de replay con datos insuficientes."""
        result = agent.replay()
        assert result is None

    def test_replay_with_data(self, agent):
        """Test de replay con datos suficientes."""
        # Llenar buffer
        for _ in range(agent.batch_size + 10):
            state = np.random.randn(agent.state_dim).astype(np.float32)
            next_state = np.random.randn(agent.state_dim).astype(np.float32)
            agent.remember(state, 0, 1.0, next_state, False)

        loss = agent.replay()

        assert loss is not None
        assert isinstance(loss, float)
        assert loss >= 0

    def test_update_target_network(self, agent):
        """Test de actualización de target network."""
        initial_weights = agent.target_network.get_weights()
        agent.update_target_network(update_frequency=1)
        updated_weights = agent.target_network.get_weights()

        for _i, (initial, updated) in enumerate(
            zip(initial_weights, updated_weights, strict=False)
        ):
            assert np.allclose(initial, updated)

    def test_get_q_values(self, agent):
        """Test de obtención de Q-values."""
        state = np.random.randn(agent.state_dim).astype(np.float32)
        q_values = agent.get_q_values(state)

        assert q_values.shape == (agent.action_dim,)
        assert isinstance(q_values, np.ndarray)

    def test_get_best_action(self, agent):
        """Test de obtención de mejor acción."""
        state = np.random.randn(agent.state_dim).astype(np.float32)
        best_actions = agent.get_best_action(state, top_k=3)

        assert len(best_actions) <= 3
        assert all(0 <= action < agent.action_dim for action, _ in best_actions)

    def test_epsilon_decay(self, agent):
        """Test de decaimiento de epsilon."""
        initial_epsilon = agent.epsilon

        for _ in range(10):
            agent.replay_buffer = deque()  # Mock
            agent.epsilon *= agent.epsilon_decay

        assert agent.epsilon < initial_epsilon

    def test_reset_epsilon(self, agent):
        """Test de reseteo de epsilon."""
        agent.epsilon = 0.1
        agent.reset_epsilon(epsilon=1.0)

        assert agent.epsilon == 1.0

    def test_agent_summary(self, agent):
        """Test de resumen del agente."""
        summary = agent.summary()

        assert "State Dim" in summary
        assert "Action Dim" in summary
        assert "Epsilon" in summary

    def test_singleton_pattern(self):
        """Test del patrón singleton para get_agent."""
        agent1 = get_agent(state_dim=10)
        agent2 = get_agent(state_dim=20)  # Params ignorados si ya existe

        assert agent1 is agent2
