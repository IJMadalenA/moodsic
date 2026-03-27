"""
Comando: python manage.py evaluate_model

Evalúa un modelo entrenado en un conjunto de prueba de interacciones.

Ejemplos:
    python manage.py evaluate_model --model-path ml/models/dqn_agent_20260325_225939.h5
    python manage.py evaluate_model --model-path ml/models/model.h5 --test-days 7
    python manage.py evaluate_model --model-path ml/models/model.h5 --show-recommendations
"""

import logging
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from ml.agent import DQNAgent
from ml.reward import get_reward_calculator
from ml.state_builder import get_state_builder
from ml.training import TrainingDataLoader, ModelEvaluator

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Evalúa un modelo DQN entrenado en datos de prueba"

    def add_arguments(self, parser):
        parser.add_argument(
            "--model-path",
            type=str,
            required=True,
            help="Ruta del modelo a evaluar (ruta obligatoria)",
        )
        parser.add_argument(
            "--test-days",
            type=int,
            default=7,
            help="Días de interacciones recientes para prueba (default: 7)",
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

    def handle(self, *args, **options):
        model_path = options["model_path"]
        test_days = options["test_days"]
        show_recommendations = options["show_recommendations"]
        verbose = options["verbose"]

        # Configurar logging
        log_level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(level=log_level)

        self.stdout.write(self.style.SUCCESS(f"\n📊 Evaluando modelo DQN"))
        self.stdout.write(f"   📁 Modelo: {model_path}")

        try:
            # 1. Verificar que el modelo existe
            if not Path(model_path).exists():
                raise FileNotFoundError(f"Modelo no encontrado: {model_path}")

            self.stdout.write(self.style.SUCCESS(f"   ✅ Archivo encontrado"))

            # 2. Cargar componentes
            self.stdout.write("\n🧠 Cargando componentes...")
            state_builder = get_state_builder()
            reward_calculator = get_reward_calculator()

            # Cargar modelo
            import tensorflow as tf
            model = tf.keras.models.load_model(model_path)
            self.stdout.write(self.style.SUCCESS("   ✅ Modelo cargado"))

            # 3. Cargar datos de prueba
            self.stdout.write(f"\n📥 Cargando datos de prueba (últimos {test_days} días)...")
            data_loader = TrainingDataLoader()
            test_interactions = data_loader.load_interactions(days=test_days)

            if not test_interactions:
                self.stdout.write(
                    self.style.WARNING("   ⚠️  No hay interacciones para evaluar, usando sintéticas")
                )
                # Generar datos sintéticos
                test_interactions = self._generate_synthetic_data(100)

            self.stdout.write(
                self.style.SUCCESS(f"   ✅ {len(test_interactions)} interacciones para prueba")
            )

            # 4. Evaluar
            self.stdout.write("\n🔍 Evaluando modelo...")
            evaluator = ModelEvaluator(
                model=model,
                state_builder=state_builder,
                reward_calculator=reward_calculator,
            )

            metrics = evaluator.evaluate_on_test_set(test_interactions)

            # 5. Mostrar resultados
            self.stdout.write(
                f"\n📈 Resultados de evaluación:\n"
                f"   Accuracy: {metrics.get('accuracy', 'N/A')}\n"
                f"   Mean Reward: {metrics.get('mean_reward', 'N/A')}\n"
                f"   Total Interactions: {metrics.get('total_interactions', len(test_interactions))}"
            )

            # 6. Mostrar recomendaciones si aplica
            if show_recommendations:
                self.stdout.write("\n🎵 Top-10 Recomendaciones del Modelo:")
                recommendations = evaluator.recommend_tracks(
                    state=self._get_sample_state(state_builder),
                    k=10,
                )
                for i, rec in enumerate(recommendations, 1):
                    self.stdout.write(f"   {i}. Track ID: {rec} (Q-value: N/A)")

            self.stdout.write(
                self.style.SUCCESS("\n✅ Evaluación completada exitosamente!\n")
            )

        except FileNotFoundError as e:
            self.stdout.write(self.style.ERROR(f"\n❌ Archivo no encontrado: {str(e)}\n"))
            raise CommandError(str(e))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n❌ Error durante la evaluación:\n{str(e)}\n"))
            raise CommandError(str(e))

    def _generate_synthetic_data(self, count: int):
        """Genera datos sintéticos para pruebas."""
        import numpy as np
        from datetime import datetime, timedelta

        from apps.interactions.models import Interaction
        from apps.music.models import Track, Album
        from django.contrib.auth import get_user_model

        User = get_user_model()

        # Obtener usuario de prueba
        user = User.objects.first()
        if not user:
            user = User.objects.create_user(username="test_eval", password="test123")

        # Obtener o crear album/track
        album, _ = Album.objects.get_or_create(name="Test Album Eval")
        track, _ = Track.objects.get_or_create(
            spotify_id="test_track_eval",
            defaults={
                "name": "Test Track",
                "album": album,
                "duration_ms": 180000,
                "explicit": False,
                "track_number": 1,
                "popularity": 80,
            },
        )

        # Crear interacciones sintéticas
        interactions = []
        for i in range(count):
            interaction = Interaction(
                user=user,
                track=track,
                feedback=np.random.choice(["completed", "skip", "replay"]),
                play_duration=np.random.randint(30, 180),
                track_duration=180,
                reward=float(np.random.uniform(-1, 1)),
                started_at=datetime.now() - timedelta(days=np.random.randint(0, 7)),
            )
            interactions.append(interaction)

        return interactions

    def _get_sample_state(self, state_builder):
        """Obtiene un estado de muestra del sistema."""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.first()

        if user:
            return state_builder.build_state(user=user)
        return None
