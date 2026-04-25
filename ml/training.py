"""
Script de Entrenamiento para el Agente RL.

Carga datos de interacciones del BD, construye estados, y entrena el agente DQN.
Guarda modelos y registra métricas para análisis.

Uso:
    python ml/training.py train --episodes 100 --batch-size 64
    python ml/training.py eval --model-path ml/models/dqn_model.h5
    python ml/training.py visualize
"""

import argparse
import json
import logging
import os

# Asegurar que el directorio raíz está en el path
import sys
from datetime import timedelta
from pathlib import Path

import django
import matplotlib.pyplot as plt
import numpy as np
from django.contrib.auth import get_user_model
from django.utils import timezone
from sklearn.preprocessing import StandardScaler

from apps.context.models import NewsContext, WeatherContext
from apps.interactions.models import Interaction, InteractionSession
from apps.music.models import Track
from ml.agent import DQNAgent, get_agent
from ml.reward import get_reward_calculator
from ml.state_builder import get_state_builder

project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

User = get_user_model()

# Directorio de modelos
MODELS_DIR = Path("ml/models")
MODELS_DIR.mkdir(exist_ok=True, parents=True)

# Directorio de logs
LOGS_DIR = Path("ml/logs")
LOGS_DIR.mkdir(exist_ok=True, parents=True)


class TrainingDataLoader:
    """
    Carga datos de interacciones del BD para entrenamiento.
    """

    @staticmethod
    def load_interactions(
        days: int = 30, limit: int | None = None
    ) -> list[Interaction]:
        """
        Carga interacciones recientes del BD.

        Args:
            days: Número de días hacia atrás
            limit: Máximo de interacciones a cargar

        Returns:
            Lista de objetos Interaction
        """
        cutoff_date = timezone.now() - timedelta(days=days)
        interactions = Interaction.objects.filter(
            created_at__gte=cutoff_date
        ).select_related("user", "track")

        if limit:
            interactions = interactions[:limit]

        logger.info(
            f"Cargadas {interactions.count()} interacciones de los últimos {days} días"
        )
        return list(interactions)

    @staticmethod
    def load_user_sessions(
        user: User, limit: int | None = None
    ) -> list[InteractionSession]:
        """
        Carga sesiones de un usuario.
        """
        sessions = InteractionSession.objects.filter(user=user).order_by("-started_at")

        if limit:
            sessions = sessions[:limit]

        return list(sessions)

    @staticmethod
    def get_top_users(min_interactions: int = 10) -> list[User]:
        """
        Obtiene usuarios con más interacciones.
        """
        from django.db.models import Count

        users = (
            User.objects.annotate(interaction_count=Count("interactions"))
            .filter(interaction_count__gte=min_interactions)
            .order_by("-interaction_count")
        )

        return list(users)


class TrainingDataBuilder:
    """
    Construye datasets de entrenamiento a partir de interacciones.
    """

    def __init__(self):
        """Inicializa el constructor de datos."""
        self.state_builder = get_state_builder()
        self.reward_calculator = get_reward_calculator()
        self.scaler = StandardScaler()

    def build_training_batch(
        self, interactions: list[Interaction]
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Construye un batch de entrenamiento a partir de interacciones.

        Args:
            interactions: Lista de interacciones

        Returns:
            Tuple de (states, rewards)
        """
        states = []
        rewards = []

        for interaction in interactions:
            try:
                # Construir estado
                weather_context = None
                if interaction.weather_id:
                    try:
                        weather = WeatherContext.objects.get(id=interaction.weather_id)
                        weather_context = {
                            "temperature": weather.temperature,
                            "humidity": weather.humidity,
                            "wind_speed": weather.wind_speed,
                            "main_status": weather.main_status,
                        }
                    except WeatherContext.DoesNotExist:
                        pass

                # Audio features del track
                audio_features = self._get_track_audio_features(interaction.track)

                news_contexts = []
                if interaction.news_ids:
                    news_items = NewsContext.objects.filter(id__in=interaction.news_ids)
                    news_contexts = [
                        {
                            "sentiment_score": item.sentiment_score,
                            "sentiment_label": item.sentiment_label,
                            "is_breaking": item.is_breaking,
                        }
                        for item in news_items
                    ]

                state = self.state_builder.build_state(
                    user=interaction.user,
                    weather_context=weather_context,
                    current_track=audio_features,
                    time_of_day=self._get_time_of_day(interaction.started_at),
                    news_contexts=news_contexts,
                )

                states.append(state)
                rewards.append(interaction.reward)

            except Exception as e:
                logger.warning(f"Error procesando interacción {interaction.id}: {e}")
                continue

        return np.array(states), np.array(rewards)

    @staticmethod
    def _get_track_audio_features(track: Track) -> dict:
        """Obtiene características de audio de un track."""
        try:
            if hasattr(track, "audio_features"):
                af = track.audio_features
                return {
                    "energy": af.energy,
                    "danceability": af.danceability,
                    "valence": af.valence,
                    "acousticness": af.acousticness,
                    "instrumentalness": af.instrumentalness,
                    "liveness": af.liveness,
                    "loudness": af.loudness,
                    "tempo": af.tempo,
                    "speechiness": af.speechiness,
                    "key": af.key,
                    "mode": af.mode,
                    "time_signature": af.time_signature,
                }
        except Exception as exc:
            logger.warning(f"Error al obtener audio features de {track.name}: {exc}")

        return {
            "energy": 0.5,
            "danceability": 0.5,
            "valence": 0.5,
            "acousticness": 0.3,
            "instrumentalness": 0.0,
            "liveness": 0.2,
            "loudness": -5,
            "tempo": 120,
            "speechiness": 0.0,
            "key": 0,
            "mode": 1,
            "time_signature": 4,
        }

    @staticmethod
    def _get_time_of_day(dt):
        """Obtiene la hora del día."""
        hour = dt.hour
        if 6 <= hour < 12:
            return "morning"
        elif 12 <= hour < 18:
            return "afternoon"
        elif 18 <= hour <= 23:
            return "evening"
        else:
            return "night"


class ModelTrainer:
    """
    Entrenam el agente DQN.
    """

    def __init__(
        self,
        agent: DQNAgent | None = None,
        state_dim: int = 45,
        action_dim: int = 100,
        episodes: int = 100,
        batch_size: int = 64,
    ):
        """Inicializa el entrenador."""
        self.agent = agent or get_agent(
            state_dim=state_dim,
            action_dim=action_dim,
        )
        self.episodes = episodes
        self.batch_size = batch_size
        self.data_builder = TrainingDataBuilder()

        self.training_logs = {
            "episode_rewards": [],
            "episode_losses": [],
            "epsilon_values": [],
            "timestamps": [],
        }

    def train_from_interactions(self, days: int = 30):
        """
        Entrena el agente usando interacciones históricas.

        Args:
            days: Número de días de datos a usar
        """
        logger.info(f"Iniciando entrenamiento con datos de {days} días...")

        # Cargar interacciones
        loader = TrainingDataLoader()
        interactions = loader.load_interactions(days=days, limit=5000)

        if len(interactions) < 100:
            logger.warning(
                f"Pocas interacciones ({len(interactions)}), usando data sintética"
            )
            self._train_with_synthetic_data()
            return

        # Construir batch de entrenamiento
        logger.info(f"Construyendo batch de {len(interactions)} interacciones...")
        states, rewards = self.data_builder.build_training_batch(interactions)

        if len(states) == 0:
            logger.error("No se pudieron construir estados")
            return

        logger.info(
            f"Estado shape: {states.shape}, Rewards: min={rewards.min():.3f}, "
            f"max={rewards.max():.3f}, mean={rewards.mean():.3f}"
        )

        # Llenar replay buffer del agente con experiencias
        logger.info("Llenando replay buffer del agente...")
        for i, state in enumerate(states):
            next_state = states[i + 1] if i + 1 < len(states) else state
            reward = rewards[i]
            done = i == len(states) - 1

            # Seleccionar acción aleatoria (exploración)
            action = np.random.randint(0, self.agent.action_dim)

            self.agent.remember(state, action, reward, next_state, done)

        logger.info(f"Replay buffer contiene {len(self.agent.memory)} experiencias")

        # Entrenar el agente
        self._run_training_loop()

    def _train_with_synthetic_data(self):
        """
        Entrena el agente con datos sintéticos para testing.
        """
        logger.info("Generando datos sintéticos para entrenamiento...")

        for episode in range(min(self.episodes, 10)):
            episode_rewards = []
            episode_loss = 0.0
            state = np.random.randn(self.agent.state_dim).astype(np.float32)

            for step in range(50):
                action = np.random.randint(0, self.agent.action_dim)
                reward = np.random.randn() * 0.5  # Reward aleatorio
                next_state = np.random.randn(self.agent.state_dim).astype(np.float32)
                done = step == 49

                self.agent.remember(state, action, reward, next_state, done)
                state = next_state
                episode_rewards.append(float(reward))

            # Entrenar con batch
            if len(self.agent.memory) >= self.agent.batch_size:
                loss = self.agent.replay()
                episode_loss = float(loss) if loss is not None else 0.0

                if episode % 2 == 0:
                    logger.info(f"Episodio {episode + 1}, Loss: {episode_loss:.4f}")

            self.training_logs["episode_rewards"].append(
                float(np.mean(episode_rewards)) if episode_rewards else 0.0
            )
            self.training_logs["episode_losses"].append(episode_loss)
            self.training_logs["epsilon_values"].append(self.agent.epsilon)
            self.training_logs["timestamps"].append(timezone.now().isoformat())

    def _run_training_loop(self):
        """Ejecuta el loop de entrenamiento."""
        logger.info(f"Iniciando {self.episodes} episodios de entrenamiento...")
        start_time = timezone.now()

        for episode in range(self.episodes):
            episode_loss_values = []

            # Entrenar con múltiples batches del replay buffer
            for _ in range(10):
                loss = self.agent.replay()
                if loss is not None:
                    episode_loss_values.append(loss)

            # Actualizar target network
            self.agent.update_target_network(update_frequency=10)

            # Registrar métricas
            avg_loss = np.mean(episode_loss_values) if episode_loss_values else 0
            self.training_logs["episode_rewards"].append(0)
            self.training_logs["episode_losses"].append(avg_loss)
            self.training_logs["epsilon_values"].append(self.agent.epsilon)
            self.training_logs["timestamps"].append(timezone.now().isoformat())

            if (episode + 1) % max(1, self.episodes // 10) == 0:
                elapsed = timezone.now() - start_time
                logger.info(
                    f"Episodio {episode + 1}/{self.episodes} - "
                    f"Loss: {avg_loss:.4f}, Epsilon: {self.agent.epsilon:.4f}, "
                    f"Tiempo: {elapsed.total_seconds():.1f}s"
                )

        total_time = timezone.now() - start_time
        logger.info(f"Entrenamiento completado en {total_time.total_seconds():.1f}s")

    def save_model(self, model_name: str = "dqn_agent") -> Path:
        """
        Guarda el modelo entrenado.

        Args:
            model_name: Nombre del archivo (sin extensión)
        """
        model_path = (
            MODELS_DIR / f"{model_name}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.h5"
        )
        self.agent.save_model(str(model_path))
        logger.info(f"Modelo guardado en: {model_path}")

        # Guardar logs de entrenamiento
        log_path = (
            LOGS_DIR / f"training_{timezone.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(log_path, "w") as f:
            json.dump(self.training_logs, f, indent=2)
        logger.info(f"Logs de entrenamiento guardados en: {log_path}")

        return model_path

    @staticmethod
    def _find_latest_log_file() -> Path | None:
        log_files = sorted(LOGS_DIR.glob("training_*.json"), reverse=True)
        return log_files[0] if log_files else None

    @staticmethod
    def visualize_logs(log_path: Path | None = None) -> None:
        """Visualiza logs de entrenamiento previamente guardados."""
        if log_path is None:
            log_path = ModelTrainer._find_latest_log_file()

        if log_path is None or not log_path.exists():
            logger.warning("No se encontró ningún log de entrenamiento para visualizar")
            return

        with open(log_path) as f:
            training_logs = json.load(f)

        episode_losses = training_logs.get("episode_losses", [])
        epsilon_values = training_logs.get("epsilon_values", [])
        episode_rewards = training_logs.get("episode_rewards", [])

        if not episode_losses and not epsilon_values and not episode_rewards:
            logger.warning("El log de entrenamiento no contiene datos visualizables")
            return

        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        if episode_losses:
            axes[0].plot(episode_losses, label="Loss")
            axes[0].set_xlabel("Episodio")
            axes[0].set_ylabel("Pérdida")
            axes[0].set_title("Pérdida durante Entrenamiento")
            axes[0].grid(True)
            axes[0].legend()

        if epsilon_values:
            axes[1].plot(epsilon_values, label="Epsilon", color="orange")
            axes[1].set_xlabel("Episodio")
            axes[1].set_ylabel("Epsilon")
            axes[1].set_title("Tasa de Exploración (Epsilon)")
            axes[1].grid(True)
            axes[1].legend()

        if episode_rewards:
            axes[0].plot(episode_rewards, label="Rewards", linestyle="--")
            axes[0].legend()

        plot_path = (
            LOGS_DIR
            / f"training_visualization_{timezone.now().strftime('%Y%m%d_%H%M%S')}.png"
        )
        plt.savefig(plot_path, dpi=100, bbox_inches="tight")
        logger.info(f"Gráfico de entrenamiento guardado en: {plot_path}")
        plt.show()
        plt.close(fig)

    def plot_training_history(self):
        """
        Grafica el histórico de entrenamiento.
        """
        if not self.training_logs["episode_losses"]:
            logger.warning("No hay datos de pérdida para graficar")
            return

        _fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        # Gráfico de pérdida
        axes[0].plot(self.training_logs["episode_losses"], label="Loss")
        axes[0].set_xlabel("Episodio")
        axes[0].set_ylabel("Pérdida")
        axes[0].set_title("Pérdida durante Entrenamiento")
        axes[0].grid(True)
        axes[0].legend()

        # Gráfico de epsilon
        axes[1].plot(
            self.training_logs["epsilon_values"], label="Epsilon", color="orange"
        )
        axes[1].set_xlabel("Episodio")
        axes[1].set_ylabel("Epsilon")
        axes[1].set_title("Tasa de Exploración (Epsilon)")
        axes[1].grid(True)
        axes[1].legend()

        plot_path = (
            LOGS_DIR / f"training_plot_{timezone.now().strftime('%Y%m%d_%H%M%S')}.png"
        )
        plt.savefig(plot_path, dpi=100, bbox_inches="tight")
        logger.info(f"Gráfico guardado en: {plot_path}")

        plt.show()


class ModelEvaluator:
    """
    Evalúa el desempeño de un modelo entrenado.
    """

    def __init__(self, model_path: str):
        """
        Inicializa el evaluador.

        Args:
            model_path: Ruta al modelo guardado
        """
        self.agent = get_agent()
        self.agent.load_model(model_path)
        self.state_builder = get_state_builder()

    def evaluate_on_test_set(self, test_interactions: list[Interaction]) -> dict:
        """
        Evalúa el modelo en un conjunto de test.

        Args:
            test_interactions: Interacciones para testing

        Returns:
            Dict con métricas de evaluación
        """
        logger.info(f"Evaluando en {len(test_interactions)} interacciones...")

        correct_predictions = 0
        total = 0

        for interaction in test_interactions:
            try:
                # Construir estado
                audio_features = self._get_track_audio_features(interaction.track)
                state = self.state_builder.build_state(
                    user=interaction.user,
                    current_track=audio_features,
                )

                # Obtener predicción del agente
                self.agent.select_action(state, training=False)

                # Comparar con feedback real
                if (interaction.feedback == "completed" and interaction.reward > 0) or (
                    interaction.feedback.startswith("skip") and interaction.reward < 0
                ):
                    correct_predictions += 1

                total += 1

            except Exception as e:
                logger.warning(f"Error en evaluación: {e}")
                continue

        accuracy = correct_predictions / total if total > 0 else 0

        metrics = {
            "accuracy": accuracy,
            "total_samples": total,
            "correct_predictions": correct_predictions,
        }

        logger.info(f"Precisión: {accuracy:.2%}")
        return metrics

    @staticmethod
    def _get_track_audio_features(track: Track) -> dict:
        """Obtiene características de audio."""
        try:
            if hasattr(track, "audio_features"):
                af = track.audio_features
                return {
                    "energy": af.energy,
                    "danceability": af.danceability,
                    "valence": af.valence,
                    "acousticness": af.acousticness,
                    "instrumentalness": af.instrumentalness,
                }
        except Exception as exc:
            logger.warning(f"Error al obtener audio features de {track.name}: {exc}")

        return {
            "energy": 0.5,
            "danceability": 0.5,
            "valence": 0.5,
            "acousticness": 0.3,
            "instrumentalness": 0.0,
        }

    def recommend_tracks(
        self, user: User, count: int = 10
    ) -> list[tuple[Track, float]]:
        """
        Recomienda tracks usando el modelo.

        Args:
            user: Usuario para el que recomendar
            count: Número de recomendaciones

        Returns:
            Lista de (Track, score) ordenada
        """
        logger.info(f"Generando {count} recomendaciones para {user.username}...")

        # Construir estado del usuario
        state = self.state_builder.build_state(user)

        # Obtener Q-values para todos los tracks
        self.agent.get_q_values(state)

        # Obtener mejores acciones
        best_actions = self.agent.get_best_action(state, top_k=count)

        recommendations = []
        for action_idx, q_value in best_actions:
            try:
                # Mapear índice de acción a track (simplificado)
                tracks = list(Track.objects.all())
                if action_idx < len(tracks):
                    track = tracks[action_idx]
                    recommendations.append((track, q_value))
            except Exception as e:
                logger.warning(f"Error mapeando acción a track: {e}")

        return recommendations


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description="Script de entrenamiento para el Agente RL de Moodsic"
    )

    subparsers = parser.add_subparsers(dest="command", help="Comando a ejecutar")

    # Comando: train
    train_parser = subparsers.add_parser("train", help="Entrenar el agente")
    train_parser.add_argument(
        "--episodes", type=int, default=50, help="Número de episodios"
    )
    train_parser.add_argument(
        "--batch-size", type=int, default=64, help="Tamaño del batch"
    )
    train_parser.add_argument(
        "--days", type=int, default=30, help="Días de datos históricos a usar"
    )
    train_parser.add_argument(
        "--save", action="store_true", help="Guardar modelo después de entrenar"
    )

    # Comando: eval
    eval_parser = subparsers.add_parser("eval", help="Evaluar un modelo")
    eval_parser.add_argument(
        "--model-path", required=True, help="Ruta al modelo guardado"
    )

    # Comando: visualize
    subparsers.add_parser("visualize", help="Visualizar datos de entrenamiento")

    args = parser.parse_args()

    if args.command == "train":
        trainer = ModelTrainer(
            episodes=args.episodes,
            batch_size=args.batch_size,
        )
        trainer.train_from_interactions(days=args.days)

        if args.save:
            trainer.save_model()
            trainer.plot_training_history()

    elif args.command == "eval":
        evaluator = ModelEvaluator(args.model_path)

        # Cargar test set
        interactions = TrainingDataLoader.load_interactions(days=7, limit=1000)
        metrics = evaluator.evaluate_on_test_set(interactions)
        logger.info(f"Métricas de evaluación: {metrics}")

    elif args.command == "visualize":
        logger.info("Visualizando datos de entrenamiento...")
        ModelTrainer.visualize_logs()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
