"""
Comando: python manage.py train_agent

Entrena el agente DQN con datos de interacciones del sistema.

Ejemplos:
    python manage.py train_agent --episodes 100
    python manage.py train_agent --episodes 50 --days 30 --batch-size 64 --save
    python manage.py train_agent --episodes 10 --visualize
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from ml.agent import get_agent
from ml.reward import get_reward_calculator
from ml.state_builder import get_state_builder
from ml.training import TrainingDataLoader, ModelTrainer, ModelEvaluator

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

    def handle(self, *args, **options):
        episodes = options["episodes"]
        days = options["days"]
        batch_size = options["batch_size"]
        save_model = options["save"]
        verbose = options["verbose"]
        visualize = options["visualize"]

        # Configurar logging
        log_level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(level=log_level)

        self.stdout.write(
            self.style.SUCCESS(f"\n>>> Iniciando entrenamiento RL ({episodes} episodios)")
        )
        self.stdout.write(f"    [DATA] Últimos {days} días")
        self.stdout.write(f"    [CONFIG] Batch size: {batch_size}")

        try:
            # 1. Cargar datos
            self.stdout.write("\n[LOAD] Cargando datos de interacciones...")
            data_loader = TrainingDataLoader()
            interactions = data_loader.load_interactions(days=days)

            self.stdout.write(
                self.style.SUCCESS(f"   [OK] {len(interactions)} interacciones cargadas")
            )

            # 2. Inicializar componentes
            self.stdout.write("\n[INIT] Inicializando componentes RL...")
            agent = get_agent(state_dim=45, action_dim=100)
            state_builder = get_state_builder()
            reward_calculator = get_reward_calculator()
            self.stdout.write(self.style.SUCCESS("   [OK] Agente, StateBuilder y RewardCalculator listos"))

            # 3. Entrenar
            self.stdout.write(f"\n[TRAIN] Entrenando por {episodes} episodios...")
            
            trainer = ModelTrainer(
                agent=agent,
                state_builder=state_builder,
                reward_calculator=reward_calculator,
                batch_size=batch_size,
            )

            history = trainer.train_from_interactions(
                interactions=interactions,
                episodes=episodes,
            )

            self.stdout.write(self.style.SUCCESS("   [OK] Entrenamiento completado"))

            # 4. Mostrar resumen
            if history:
                avg_loss = sum(history.get("losses", [])) / len(history.get("losses", [1]))
                avg_reward = sum(history.get("rewards", [])) / len(history.get("rewards", [0]))
                self.stdout.write(
                    f"\n[SUMMARY]\n"
                    f"   Loss promedio: {avg_loss:.4f}\n"
                    f"   Reward promedio: {avg_reward:.4f}\n"
                    f"   Epsilon final: {history.get('epsilon', 'N/A')}"
                )

            # 5. Guardar si aplica
            if save_model:
                self.stdout.write("\n[SAVE] Guardando modelo...")
                model_path = trainer.save_model()
                self.stdout.write(self.style.SUCCESS(f"   [OK] Modelo guardado: {model_path}"))

            # 6. Visualizar si aplica
            if visualize:
                self.stdout.write("\n[PLOT] Generando gráficos...")
                try:
                    trainer.plot_training_history(history)
                    self.stdout.write(self.style.SUCCESS("   [OK] Gráficos generados"))
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f"   [WARNING] No se pudieron generar gráficos: {e}")
                    )

            self.stdout.write(
                self.style.SUCCESS("\n[SUCCESS] Entrenamiento finalizado exitosamente!\n")
            )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n❌ Error durante el entrenamiento:\n{str(e)}\n"))
            raise CommandError(str(e))
