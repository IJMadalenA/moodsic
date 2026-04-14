"""
Comando: python manage.py evaluate_model

Evalúa un modelo entrenado en un conjunto de prueba de interacciones.

Ejemplos:
    python manage.py evaluate_model --model-path ml/models/dqn_agent_20260325_225939.h5
    python manage.py evaluate_model --model-path ml/models/model.h5 --test-days 7
    python manage.py evaluate_model --model-path ml/models/model.h5 --show-recommendations
    python manage.py evaluate_model --with-synthetic-context --auto-train --benchmark-episodes 5
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from apps.interactions.services.reward_service import get_reward_service
from ml.state_builder import get_state_builder
from ml.training import LOGS_DIR, MODELS_DIR, ModelEvaluator, ModelTrainer, TrainingDataLoader

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Evalúa un modelo DQN entrenado en datos de prueba"

    def add_arguments(self, parser):
        parser.add_argument(
            "--model-path",
            type=str,
            default=None,
            help="Ruta del modelo a evaluar (si se omite, se busca el último modelo)",
        )
        parser.add_argument(
            "--test-days",
            type=int,
            default=7,
            help="Días de interacciones recientes para prueba (default: 7)",
        )
        parser.add_argument(
            "--test-limit",
            type=int,
            default=1000,
            help="Máximo de interacciones a usar en evaluación (default: 1000)",
        )
        parser.add_argument(
            "--show-recommendations",
            action="store_true",
            help="Mostrar top-10 recommendations generadas por el modelo",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Mostrar logs detallados",
        )
        parser.add_argument(
            "--with-synthetic-context",
            action="store_true",
            help="Seed offline de contexto e interacciones antes de evaluar",
        )
        parser.add_argument(
            "--auto-train",
            action="store_true",
            help="Entrenar un modelo rápidamente antes de evaluar (útil con --with-synthetic-context)",
        )
        parser.add_argument(
            "--benchmark-episodes",
            type=int,
            default=5,
            help="Episodios para auto-train en benchmark offline (default: 5)",
        )
        parser.add_argument(
            "--benchmark-output",
            type=str,
            default=None,
            help="Ruta JSON para guardar resultados del benchmark (default: ml/logs)",
        )
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument("--synthetic-users", type=int, default=3)
        parser.add_argument("--synthetic-tracks", type=int, default=30)
        parser.add_argument("--synthetic-interactions", type=int, default=600)
        parser.add_argument("--synthetic-weather", type=int, default=60)
        parser.add_argument("--synthetic-news", type=int, default=120)

    def handle(self, *args, **options):
        model_path = options["model_path"]
        test_days = options["test_days"]
        test_limit = options["test_limit"]
        show_recommendations = options["show_recommendations"]
        verbose = options["verbose"]
        offline = options["with_synthetic_context"]
        auto_train = options["auto_train"]

        # Configurar logging
        log_level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(level=log_level)

        self.stdout.write(self.style.SUCCESS("\n📊 Evaluando modelo DQN"))

        try:
            if offline:
                self.stdout.write("\n[SEED] Generando contexto sintético offline...")
                call_command(
                    "seed_synthetic_context",
                    weather_count=options["synthetic_weather"],
                    news_count=options["synthetic_news"],
                    days_back=max(test_days, 7),
                    seed=options["seed"],
                    clear_existing=True,
                )
                self.stdout.write(self.style.SUCCESS("   ✅ Contexto sintético generado"))

                self.stdout.write("\n[SEED] Generando interacciones sintéticas...")
                call_command(
                    "seed_synthetic_interactions",
                    users=options["synthetic_users"],
                    tracks=options["synthetic_tracks"],
                    interactions=options["synthetic_interactions"],
                    seed=options["seed"],
                )
                self.stdout.write(self.style.SUCCESS("   ✅ Interacciones sintéticas generadas"))

            if auto_train:
                self.stdout.write("\n[TRAIN] Entrenando modelo rápido para benchmark...")
                trainer = ModelTrainer(
                    episodes=options["benchmark_episodes"],
                    batch_size=64,
                )
                trainer.train_from_interactions(days=max(test_days, 7))
                trainer.save_model(model_name="dqn_benchmark")
                model_path = self._resolve_model_path(None)
                self.stdout.write(self.style.SUCCESS(f"   ✅ Modelo benchmark: {model_path}"))

            model_path = self._resolve_model_path(model_path)
            self.stdout.write(f"   📁 Modelo: {model_path}")

            self.stdout.write(f"\n📥 Cargando datos de prueba (últimos {test_days} días)...")
            test_interactions = TrainingDataLoader.load_interactions(
                days=test_days,
                limit=test_limit,
            )
            if not test_interactions:
                raise CommandError(
                    "No hay interacciones para evaluar. Ejecuta seed_synthetic_interactions o usa --with-synthetic-context."
                )

            self.stdout.write(
                self.style.SUCCESS(f"   ✅ {len(test_interactions)} interacciones para prueba")
            )

            self.stdout.write("\n🔍 Evaluando modelo...")
            evaluator = ModelEvaluator(model_path)
            metrics = evaluator.evaluate_on_test_set(test_interactions)
            mean_reward = (
                sum(inter.reward for inter in test_interactions) / len(test_interactions)
                if test_interactions
                else 0.0
            )

            self.stdout.write(
                f"\n📈 Resultados de evaluación:\n"
                f"   Accuracy: {metrics.get('accuracy', 'N/A')}\n"
                f"   Mean Reward (dataset): {mean_reward:.4f}\n"
                f"   Total Samples: {metrics.get('total_samples', len(test_interactions))}"
            )

            benchmark_data = {
                "timestamp": datetime.now().isoformat(),
                "model_path": str(model_path),
                "options": {
                    "test_days": test_days,
                    "test_limit": test_limit,
                    "with_synthetic_context": offline,
                    "auto_train": auto_train,
                    "benchmark_episodes": options["benchmark_episodes"],
                    "seed": options["seed"],
                },
                "metrics": {
                    **metrics,
                    "mean_reward_dataset": float(mean_reward),
                },
            }
            output_path = self._write_benchmark_json(
                benchmark_data,
                output=options["benchmark_output"],
            )
            self.stdout.write(self.style.SUCCESS(f"   ✅ Benchmark guardado: {output_path}"))

            # Mostrar recomendaciones si aplica
            if show_recommendations:
                self.stdout.write("\n🎵 Top-10 Recomendaciones del Modelo:")
                sample_user = self._get_sample_user()
                recommendations = evaluator.recommend_tracks(sample_user, count=10)
                for i, rec in enumerate(recommendations, 1):
                    track, score = rec
                    self.stdout.write(
                        f"   {i}. Track ID: {track.id} | {track.name} (score={score:.4f})"
                    )

            self.stdout.write(
                self.style.SUCCESS("\n✅ Evaluación completada exitosamente!\n")
            )

        except FileNotFoundError as e:
            self.stdout.write(self.style.ERROR(f"\n❌ Archivo no encontrado: {str(e)}\n"))
            raise CommandError(str(e))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n❌ Error durante la evaluación:\n{str(e)}\n"))
            raise CommandError(str(e))

    @staticmethod
    def _resolve_model_path(model_path: str | None) -> str:
        if model_path:
            if not Path(model_path).exists():
                raise FileNotFoundError(f"Modelo no encontrado: {model_path}")
            return model_path

        model_files = sorted(MODELS_DIR.glob("*.h5"), reverse=True)
        if not model_files:
            raise FileNotFoundError(
                "No se encontró ningún modelo .h5 en ml/models. Usa --auto-train o --model-path."
            )
        return str(model_files[0])

    @staticmethod
    def _write_benchmark_json(payload: dict, output: str | None = None) -> str:
        if output:
            output_path = Path(output)
        else:
            output_path = LOGS_DIR / f"evaluation_benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        return str(output_path)

    @staticmethod
    def _get_sample_user():
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.first()
        if user is None:
            raise CommandError("No hay usuarios disponibles para mostrar recomendaciones")
        return user
