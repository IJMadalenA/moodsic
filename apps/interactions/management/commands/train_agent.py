"""
Comando: uv run manage.py train_agent

Entrena el agente DQN con datos de interacciones del sistema.

Ejemplos:
    uv run manage.py train_agent --episodes 100
    uv run manage.py train_agent --episodes 50 --days 30 --batch-size 64 --save
    uv run manage.py train_agent --episodes 10 --visualize
    uv run manage.py train_agent --with-synthetic-context --episodes 20
"""

import logging

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from ml.agent import get_agent
from ml.training import ModelTrainer

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Entrena el agente DQN con datos de interacciones del sistema"

    def add_arguments(self, parser):
        parser.add_argument(
            "--episodes",
            type=int,
            default=50,
            help="Número de episodios de entrenamiento (default: 50)",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Días de historial de interacciones a usar (default: 30)",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=64,
            help="Tamaño de batch para el entrenamiento (default: 64)",
        )
        parser.add_argument(
            "--save",
            action="store_true",
            help="Guardar el modelo después del entrenamiento",
        )
        parser.add_argument(
            "--model-path",
            type=str,
            default=None,
            help="Ruta para guardar/cargar el modelo",
        )
        parser.add_argument(
            "--visualize",
            action="store_true",
            help="Visualizar métricas de entrenamiento después",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Mostrar logs detallados",
        )
        parser.add_argument(
            "--with-synthetic-context",
            action="store_true",
            help="Seed de contexto e interacciones sintéticas antes de entrenar",
        )
        parser.add_argument(
            "--synthetic-users",
            type=int,
            default=3,
            help="Usuarios sintéticos para el seed offline (default: 3)",
        )
        parser.add_argument(
            "--synthetic-tracks",
            type=int,
            default=30,
            help="Tracks sintéticos para el seed offline (default: 30)",
        )
        parser.add_argument(
            "--synthetic-interactions",
            type=int,
            default=600,
            help="Interacciones sintéticas para el seed offline (default: 600)",
        )
        parser.add_argument(
            "--synthetic-weather",
            type=int,
            default=60,
            help="Registros de clima sintético (default: 60)",
        )
        parser.add_argument(
            "--synthetic-news",
            type=int,
            default=120,
            help="Registros de noticias sintéticas (default: 120)",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=42,
            help="Semilla para generación sintética reproducible",
        )

    def handle(self, *args, **options):
        episodes = options["episodes"]
        days = options["days"]
        batch_size = options["batch_size"]
        save_model = options["save"]
        verbose = options["verbose"]
        visualize = options["visualize"]
        with_synthetic_context = options["with_synthetic_context"]

        # Configurar logging
        log_level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(level=log_level)

        self.stdout.write(
            self.style.SUCCESS(f"\n>>> Iniciando entrenamiento RL ({episodes} episodios)")
        )
        self.stdout.write(f"    [DATA] Últimos {days} días")
        self.stdout.write(f"    [CONFIG] Batch size: {batch_size}")

        try:
            if with_synthetic_context:
                self.stdout.write("\n[SEED] Generando contexto sintético offline...")
                call_command(
                    "seed_synthetic_context",
                    weather_count=options["synthetic_weather"],
                    news_count=options["synthetic_news"],
                    days_back=max(days, 7),
                    seed=options["seed"],
                    clear_existing=True,
                )
                self.stdout.write(self.style.SUCCESS("   [OK] Contexto sintético generado"))

                self.stdout.write("\n[SEED] Generando interacciones sintéticas...")
                call_command(
                    "seed_synthetic_interactions",
                    users=options["synthetic_users"],
                    tracks=options["synthetic_tracks"],
                    interactions=options["synthetic_interactions"],
                    seed=options["seed"],
                )
                self.stdout.write(self.style.SUCCESS("   [OK] Interacciones sintéticas generadas"))

            # 1. Inicializar componentes
            self.stdout.write("\n[INIT] Inicializando componentes RL...")
            agent = get_agent(state_dim=45, action_dim=100)
            self.stdout.write(self.style.SUCCESS("   [OK] Agente listo"))

            # 2. Entrenar
            self.stdout.write(f"\n[TRAIN] Entrenando por {episodes} episodios...")

            trainer = ModelTrainer(
                agent=agent,
                episodes=episodes,
                batch_size=batch_size,
            )

            trainer.train_from_interactions(days=days)

            self.stdout.write(self.style.SUCCESS("   [OK] Entrenamiento completado"))

            # 3. Mostrar resumen
            losses = trainer.training_logs.get("episode_losses", [])
            rewards = trainer.training_logs.get("episode_rewards", [])
            epsilons = trainer.training_logs.get("epsilon_values", [])
            avg_loss = (sum(losses) / len(losses)) if losses else 0.0
            avg_reward = (sum(rewards) / len(rewards)) if rewards else 0.0
            epsilon_final = epsilons[-1] if epsilons else "N/A"
            self.stdout.write(
                f"\n[SUMMARY]\n"
                f"   Loss promedio: {avg_loss:.4f}\n"
                f"   Reward promedio: {avg_reward:.4f}\n"
                f"   Epsilon final: {epsilon_final}"
            )

            # 4. Guardar si aplica
            if save_model:
                self.stdout.write("\n[SAVE] Guardando modelo...")
                model_path = trainer.save_model()
                self.stdout.write(self.style.SUCCESS(f"   [OK] Modelo guardado: {model_path}"))

            # 5. Visualizar si aplica
            if visualize:
                self.stdout.write("\n[PLOT] Generando gráficos...")
                try:
                    trainer.plot_training_history()
                    self.stdout.write(self.style.SUCCESS("   [OK] Gráficos generados"))
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f"   [WARNING] No se pudieron generar gráficos: {e}")
                    )

            self.stdout.write(
                self.style.SUCCESS("\n[SUCCESS] Entrenamiento finalizado exitosamente!\n")
            )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n❌ Error durante el entrenamiento:\n{e!s}\n"))
            raise CommandError(str(e))
