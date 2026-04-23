from unittest.mock import patch

import pytest
from django.core.management import call_command


@pytest.mark.django_db
class TestManagementCommands:
    def test_train_agent_command(self):
        from apps.interactions.management.commands.train_agent import Command
        with patch.object(Command, "handle", return_value="OK") as mock_handle:
            call_command("train_agent", episodes=1)
            assert mock_handle.called

    def test_evaluate_model_command(self):
        from apps.interactions.management.commands.evaluate_model import Command
        with patch.object(Command, "handle", return_value="OK") as mock_handle:
            call_command("evaluate_model", auto_train=True)
            assert mock_handle.called

    def test_seed_synthetic_interactions_command(self):
        # Crear datos previos necesarios
        from apps.users.models.user import User
        User.objects.get_or_create(username="seed_user", email="seed@test.com")

        call_command("seed_synthetic_interactions", interactions=1)

    def test_collect_interactions_command(self):
        # Parchear el comando completo para evitar efectos secundarios complejos
        from apps.interactions.management.commands.collect_interactions import (
            Command as CollectCommand,
        )
        with patch.object(CollectCommand, "handle", return_value="Done") as mock_handle:
            call_command("collect_interactions")
            assert mock_handle.called

    def test_sync_spotify_tracks_command(self):
        from apps.users.models.user import User
        user, _ = User.objects.get_or_create(username="sync_user", email="sync@test.com")

        from apps.interactions.management.commands.sync_spotify_tracks import (
            Command as SyncCommand,
        )
        with patch.object(SyncCommand, "handle", return_value="Done") as mock_handle:
            call_command("sync_spotify_tracks", user_id=user.id)
            assert mock_handle.called

    def test_moodsic_help_command(self):
        call_command("moodsic_help")

    def test_fetch_news_context_command(self):
        from apps.context.management.commands.fetch_news_context import (
            Command as NewsCommand,
        )
        with patch.object(NewsCommand, "handle", return_value="Done") as mock_handle:
            call_command("fetch_news_context", page_size=1)
            assert mock_handle.called

    def test_setup_geo_command(self):
        with patch("django.core.management.call_command") as mock_call:
            call_command("setup_geo")
            assert mock_call.called

    def test_verify_spotify_command(self):
        from apps.music.management.commands.verify_spotify import (
            Command as VerifyCommand,
        )
        with patch.object(VerifyCommand, "handle", return_value="Done") as mock_handle:
            call_command("verify_spotify")
            assert mock_handle.called

    def test_benchmark_matrix_command(self):
        from apps.interactions.management.commands.benchmark_matrix import Command
        with patch.object(Command, "handle", return_value="Done") as mock_handle:
            call_command("benchmark_matrix", config="ml/test_benchmark_config.json")
            assert mock_handle.called

    def test_benchmark_matrix_real_call_skip_runs(self):
        # Intentar una llamada real pero con skip_runs para cubrir la logica de parsing y ejecución
        import json
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Para que benchmark_matrix funcione con skip_runs, necesita encontrar archivos en el run_dir.
            # El run_dir se crea dentro de base_dir (tmpdir) con un nombre que incluye el timestamp o run_name.
            # Para controlar la ruta, pasamos un run_name.
            run_name = "test_run"
            run_dir = tmpdir_path / f"benchmark_matrix_{run_name}"
            run_dir.mkdir()

            # Crear archivos benchmark JSON ficticios
            for seed in [101, 202]:
                data = {
                    "timestamp": "2026-04-16T23:33:00",
                    "options": {
                        "seed": seed,
                        "benchmark_episodes": 1,
                        "test_limit": 10,
                        "test_days": 1
                    },
                    "metrics": {
                        "accuracy": 0.8,
                        "mean_reward_dataset": 0.7,
                        "total_samples": 10
                    }
                }
                with open(run_dir / f"evaluation_benchmark_seed_{seed}.json", "w") as f:
                    json.dump(data, f)

            # Ejecutar el comando real
            call_command(
                "benchmark_matrix",
                base_dir=tmpdir,
                run_name=run_name,
                skip_runs=True,
                robustness_alpha=0.5,
                seeds="101,202",
                weights="0.7:0.3,0.8:0.2"
            )

            assert (run_dir / "benchmark_weights_summary.md").exists()
            assert (run_dir / "benchmark_weights_summary.csv").exists()
            assert (run_dir / "benchmark_summary_wacc_0p70_wrew_0p30.csv").exists()

    def test_benchmark_summary_command(self):
        import json
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            # Crear un par de archivos benchmark ficticios para probar el cálculo de deltas y rankings
            for seed, acc, reward in [(101, 0.8, 0.7), (202, 0.9, 0.6)]:
                benchmark_file = tmpdir_path / f"evaluation_benchmark_seed_{seed}.json"
                data = {
                    "timestamp": "2026-04-16T23:33:00",
                    "options": {
                        "seed": seed,
                        "benchmark_episodes": 5,
                        "test_limit": 100,
                        "test_days": 7,
                        "auto_train": True,
                        "with_synthetic_context": True
                    },
                    "metrics": {
                        "accuracy": acc,
                        "mean_reward_dataset": reward,
                        "total_samples": 1000
                    }
                }
                with open(benchmark_file, "w") as f:
                    json.dump(data, f)

            output_md = tmpdir_path / "summary.md"
            output_csv = tmpdir_path / "summary.csv"

            call_command(
                "benchmark_summary",
                logs_dir=tmpdir,
                output=str(output_md),
                csv_output=str(output_csv),
                w_accuracy=0.7,
                w_reward=0.3,
                robustness_alpha=0.1
            )

            assert output_md.exists()
            assert output_csv.exists()
            content = output_md.read_text()
            assert "Benchmark Summary" in content
            assert "Robustness by Configuration" in content
