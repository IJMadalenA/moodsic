from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command

from apps.music.models import Album, Track
from apps.users.models.user import User


@pytest.mark.django_db
class TestCommandsRobust:
    @pytest.fixture
    def user(self):
        return User.objects.create_user(username="cmd_user", email="cmd@test.com")

    @patch(
        "apps.interactions.management.commands.sync_spotify_tracks.SpotifyMusicService"
    )
    def test_sync_spotify_tracks_audio_features(self, mock_service_class, user):
        user.is_spotify_connected = True
        user.save()
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service

        # Mock data
        mock_service.get_user_liked_tracks.return_value = [
            {
                "id": "t1",
                "name": "T",
                "uri": "u",
                "duration_ms": 1,
                "track_number": 1,
                "album": {"id": "al1", "name": "A"},
                "artists": [{"id": "ar1", "name": "Ar"}],
            }
        ]
        # Proporcionar todos los campos obligatorios para TrackAudioFeatures
        mock_service.get_audio_features.return_value = {
            "t1": {
                "energy": 0.8,
                "valence": 0.8,
                "danceability": 0.7,
                "acousticness": 0.1,
                "instrumentalness": 0.0,
                "liveness": 0.1,
                "loudness": -5.0,
                "speechiness": 0.05,
                "tempo": 120.0,
                "key": 1,
                "mode": 1,
                "time_signature": 4,
            }
        }

        call_command("sync_spotify_tracks", user_id=user.id, save_audio_features=True)
        assert Track.objects.filter(spotify_id="t1").exists()
        from apps.music.models import TrackAudioFeatures

        assert TrackAudioFeatures.objects.filter(track__spotify_id="t1").exists()

    @patch("apps.interactions.management.commands.collect_interactions.Interaction")
    def test_collect_interactions_real_handle(self, mock_interaction, user):
        from apps.interactions.models import Interaction
        from apps.music.models import Track

        al = Album.objects.create(name="A", spotify_id="al_coll")
        tr = Track.objects.create(
            name="T", spotify_id="tr_coll", album=al, track_number=1, duration_ms=1000
        )
        Interaction.objects.create(
            user=user, track=tr, feedback="like", play_duration=10, track_duration=100
        )

        # Probar con report y session
        import tempfile

        with tempfile.TemporaryDirectory():
            call_command(
                "collect_interactions",
                days=1,
                generate_report=True,
                save_session=True,
            )
            assert mock_interaction.objects.filter.called

    @patch("apps.interactions.management.commands.collect_interactions.Interaction")
    def test_collect_interactions_user_filter(self, mock_interaction, user):
        call_command("collect_interactions", days=1, user_id=user.id)
        assert mock_interaction.objects.filter.called

    @patch("apps.interactions.management.commands.train_agent.ModelTrainer")
    def test_train_agent_real_handle(self, mock_trainer_class):
        mock_trainer = MagicMock()
        mock_trainer_class.return_value = mock_trainer
        # Proporcionar logs para el resumen final
        mock_trainer.training_logs = {
            "episode_losses": [0.1],
            "episode_rewards": [0.5],
            "epsilon_values": [0.9],
        }

        call_command("train_agent", episodes=1)
        assert mock_trainer.train_from_interactions.called

    @patch("apps.interactions.management.commands.evaluate_model.ModelEvaluator")
    @patch("apps.interactions.management.commands.evaluate_model.TrainingDataLoader")
    @patch("apps.interactions.management.commands.evaluate_model.Path.exists")
    @patch("apps.interactions.management.commands.evaluate_model.ModelTrainer")
    def test_evaluate_model_auto_train(
        self, mock_trainer, mock_exists, mock_loader, mock_evaluator_class, user
    ):
        from apps.interactions.models import Interaction
        from apps.music.models import Track

        al = Album.objects.create(name="A", spotify_id="al_eval")
        tr = Track.objects.create(
            name="T", spotify_id="tr_eval", album=al, track_number=1, duration_ms=1000
        )
        Interaction.objects.create(
            user=user, track=tr, feedback="like", play_duration=10, track_duration=100
        )

        mock_exists.return_value = True
        mock_evaluator = MagicMock()
        mock_evaluator_class.return_value = mock_evaluator
        mock_evaluator.evaluate_on_test_set.return_value = {"accuracy": 0.9}
        mock_loader.load_interactions.return_value = Interaction.objects.all()

        call_command("evaluate_model", auto_train=True, benchmark_episodes=1)
        assert mock_trainer.called

    @patch(
        "apps.interactions.management.commands.benchmark_matrix.Command._run_evaluate_subprocess"
    )
    def test_benchmark_matrix_handle(self, mock_run):
        # Probar que el parsing de argumentos y el setup funcionan
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            # Simular archivos generados por subprocess
            run_dir = tmpdir_path / "benchmark_matrix_test"
            run_dir.mkdir()

            # Crear un archivo JSON de benchmark
            eval_file = run_dir / "evaluation_benchmark_seed_101.json"
            with open(eval_file, "w") as f:
                json.dump({"metrics": {"accuracy": 0.8, "mean_reward_dataset": 0.7}}, f)

            # Mock para que no intente leer archivos que no existen al final
            # Pero queremos que pase por la consolidación
            call_command(
                "benchmark_matrix",
                base_dir=tmpdir,
                run_name="test",
                benchmark_episodes=1,
                seeds="101",
                alphas="0.1,0.5",
                weights="0.7:0.3",
            )
            assert mock_run.called

    def test_benchmark_matrix_helpers(self):
        from apps.interactions.management.commands.benchmark_matrix import Command

        cmd = Command()
        assert cmd._weight_slug(0.7, 0.3) == "wacc_0p70_wrew_0p30"
        assert cmd._alpha_slug(0.1) == "alpha_0p10"
        assert cmd._fmt_float(0.123456) == "0.1235"

    def test_benchmark_matrix_parsing(self):
        from apps.interactions.management.commands.benchmark_matrix import Command

        cmd = Command()
        seeds = cmd._parse_seeds("101, 202, 303")
        assert seeds == [101, 202, 303]

        weights = cmd._parse_weights("0.7:0.3, 0.5:0.5")
        assert weights == [(0.7, 0.3), (0.5, 0.5)]

        alphas = cmd._parse_alphas("0.1, 0.2", 0.5)
        assert alphas == [0.1, 0.2]

    @patch("apps.music.management.commands.verify_spotify.SpotifyMusicService")
    def test_verify_spotify_real_handle(self, mock_service_class):
        mock_service_class.verify_api_connection.return_value = (True, "OK")
        call_command("verify_spotify")
        assert mock_service_class.verify_api_connection.called

    @patch(
        "apps.interactions.management.commands.sync_spotify_tracks.SpotifyMusicService"
    )
    def test_sync_spotify_tracks_from_playlist(self, mock_service_class, user):
        user.is_spotify_connected = True
        user.save()
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service

        mock_service.get_playlist_tracks.return_value = [
            {
                "id": "tp1",
                "name": "TP",
                "uri": "up",
                "duration_ms": 1,
                "track_number": 1,
                "album": {"id": "alp1", "name": "AP"},
                "artists": [{"id": "arp1", "name": "ArP"}],
            }
        ]

        call_command("sync_spotify_tracks", user_id=user.id, playlist_id="playlist123")
        assert Track.objects.filter(spotify_id="tp1").exists()
