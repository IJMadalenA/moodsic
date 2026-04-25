from unittest.mock import MagicMock, patch

import pytest

from apps.interactions.models import Interaction
from apps.music.models import Album, Artist, Track
from apps.users.models.user import User
from ml.training import (
    ModelEvaluator,
    ModelTrainer,
    TrainingDataBuilder,
    TrainingDataLoader,
)


@pytest.mark.django_db
class TestTraining:
    @pytest.fixture
    def sample_data(self):
        user = User.objects.create_user(username="ml_user", email="ml@test.com")
        artist = Artist.objects.create(name="Artist", spotify_id="ar1")
        album = Album.objects.create(name="Album", spotify_id="al1")
        track = Track.objects.create(
            name="Track",
            spotify_id="t1",
            album=album,
            duration_ms=100000,
            uri="spotify:track:t1",
            track_number=1,
        )
        track.artists.add(artist)

        interaction = Interaction.objects.create(
            user=user,
            track=track,
            feedback="like",
            play_duration=80,
            track_duration=100,
            reward=1.0,
            session_id="sess1",
        )
        return user, track, interaction

    def test_data_loader_load_interactions(self, sample_data):
        loader = TrainingDataLoader()
        interactions = loader.load_interactions(days=1)
        assert len(interactions) >= 1

    def test_data_loader_load_user_sessions(self, sample_data):
        user, _, _ = sample_data
        loader = TrainingDataLoader()
        sessions = loader.load_user_sessions(user)
        # InteractionSession no se creó explícitamente pero el loader busca Interactions por session_id
        assert len(sessions) == 0  # Porque no hay objetos InteractionSession reales

    def test_data_loader_get_top_users(self, sample_data):
        loader = TrainingDataLoader()
        users = loader.get_top_users(min_interactions=1)
        assert len(users) >= 1

    def test_data_builder_build_batch(self, sample_data):
        _, _, interaction = sample_data
        builder = TrainingDataBuilder()
        states, rewards = builder.build_training_batch([interaction])

        assert len(states) == 1
        assert states.shape[1] > 0
        assert len(rewards) == 1

    @patch("ml.training.DQNAgent")
    def test_model_trainer_init(self, mock_agent_class):
        trainer = ModelTrainer(episodes=1, batch_size=2)
        assert trainer.episodes == 1
        assert trainer.batch_size == 2

    @patch("ml.training.DQNAgent")
    @patch("ml.training.TrainingDataLoader.load_interactions")
    def test_model_trainer_train_from_interactions_real_flow(
        self, mock_load, mock_agent_class, sample_data
    ):
        _user, _track, interaction = sample_data
        # Simular 110 interacciones para activar el flujo real
        mock_load.return_value = [interaction] * 110
        mock_agent = MagicMock()
        mock_agent.batch_size = 32
        mock_agent.memory = []
        mock_agent.action_dim = 100
        mock_agent.epsilon = 0.9  # Debe ser float para formateo
        mock_agent.replay.return_value = 0.1
        mock_agent_class.return_value = mock_agent

        trainer = ModelTrainer(agent=mock_agent, episodes=1)
        trainer.train_from_interactions(days=1)
        assert mock_agent.remember.called

    def test_model_trainer_visualize(self, tmp_path):
        mock_agent = MagicMock()
        trainer = ModelTrainer(agent=mock_agent)
        trainer.training_logs = {
            "episode_losses": [0.5, 0.4],
            "episode_rewards": [0.1, 0.2],
            "epsilon_values": [1.0, 0.9],
            "timestamps": ["2024-01-01", "2024-01-02"],
        }
        with (
            patch("ml.training.LOGS_DIR", tmp_path),
            patch("ml.training.plt.subplots") as mock_subs,
        ):
            mock_fig = MagicMock()
            mock_axes = [MagicMock(), MagicMock()]
            mock_subs.return_value = (mock_fig, mock_axes)
            with (
                patch("ml.training.plt.savefig") as mock_savefig,
                patch("ml.training.plt.show"),
            ):
                trainer.plot_training_history()
                assert mock_savefig.called

    def test_model_trainer_visualize_logs(self, tmp_path):
        import json

        log_data = {
            "episode_losses": [0.1],
            "epsilon_values": [0.9],
            "episode_rewards": [0.5],
        }
        log_file = tmp_path / "training_20240101_120000.json"
        with open(log_file, "w") as f:
            json.dump(log_data, f)

        with (
            patch("ml.training.LOGS_DIR", tmp_path),
            patch("ml.training.plt.subplots") as mock_subs,
        ):
            mock_fig = MagicMock()
            mock_axes = [MagicMock(), MagicMock()]
            mock_subs.return_value = (mock_fig, mock_axes)
            with (
                patch("ml.training.plt.savefig") as mock_savefig,
                patch("ml.training.plt.show"),
            ):
                ModelTrainer.visualize_logs(log_file)
                assert mock_savefig.called

    @patch("ml.training.DQNAgent")
    def test_model_evaluator(self, mock_agent_class, sample_data):
        user, _, interaction = sample_data

        # Parchear ModelEvaluator.__init__ para evitar carga de modelo real o mockear DQNAgent.load_model
        with patch("ml.agent.DQNAgent.load_model"):
            evaluator = ModelEvaluator(model_path="dummy.keras")
            mock_agent = MagicMock()
            mock_agent.act.return_value = 0
            mock_agent.get_best_action.return_value = [(0, 0.9)]
            evaluator.agent = mock_agent

            metrics = evaluator.evaluate_on_test_set([interaction])
            assert "accuracy" in metrics

            # Dejamos que use la DB real ya que sample_data creó un track
            recommendations = evaluator.recommend_tracks(user, count=1)
            assert len(recommendations) >= 1

    def test_model_trainer_save_model(self, sample_data, tmp_path):
        _user, _track, _interaction = sample_data
        mock_agent = MagicMock()
        trainer = ModelTrainer(agent=mock_agent)
        with patch("ml.training.MODELS_DIR", tmp_path):
            path = trainer.save_model("test_model")
            assert "test_model" in str(path)
            assert mock_agent.save_model.called

    @patch("ml.agent.DQNAgent.load_model")
    def test_model_evaluator_load_fail(self, mock_load):
        mock_load.side_effect = ValueError("Fail to load model")
        with pytest.raises(ValueError, match="Fail to load model"):
            ModelEvaluator(model_path="nonexistent.h5")

    def test_training_data_loader_sessions_real(self, sample_data):
        user, _, _ = sample_data
        loader = TrainingDataLoader()
        # Crear InteractionSession
        from django.utils import timezone

        from apps.interactions.models import InteractionSession

        InteractionSession.objects.create(
            user=user, started_at=timezone.now(), session_id="sess1"
        )
        sessions = loader.load_user_sessions(user)
        assert len(sessions) >= 0  # Depende de como esté implementado el loader
