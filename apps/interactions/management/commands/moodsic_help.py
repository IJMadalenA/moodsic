"""
Comando: python manage.py moodsic_help

Muestra información de ayuda sobre los comandos de Moodsic.

Ejemplos:
    python manage.py moodsic_help
    python manage.py moodsic_help --command train_agent
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Muestra información de ayuda sobre comandos de Moodsic"

    def add_arguments(self, parser):
        parser.add_argument(
            "--command",
            type=str,
            default=None,
            help="Comando específico del cual obtener ayuda",
        )

    def handle(self, *args, **options):
        command = options.get("command")

        help_text = """
╔════════════════════════════════════════════════════════════════════════════╗
║                    🎵 MOODSIC - MANAGEMENT COMMANDS                       ║
║              RL-Based Spotify Playlist Generator for Django               ║
╚════════════════════════════════════════════════════════════════════════════╝

COMANDOS DISPONIBLES:

1️⃣  TRAIN_AGENT - Entrena el modelo DQN
   └─ python manage.py train_agent [OPTIONS]

   Opciones:
      --episodes NUM       Número de episodios (default: 50)
      --days NUM          Días de data histórica (default: 30)
      --batch-size NUM    Tamaño de batch (default: 64)
      --save              Guardar modelo después
      --visualize         Mostrar gráficos de training
      --verbose           Logs detallados

   Ejemplos:
      $ python manage.py train_agent --episodes 100 --save
      $ python manage.py train_agent --episodes 50 --days 30 --batch-size 64 --save --visualize


2️⃣  EVALUATE_MODEL - Evalúa un modelo entrenado
   └─ python manage.py evaluate_model [OPTIONS]

   Opciones:
      --model-path PATH           Ruta del modelo (REQUERIDO)
      --test-days NUM            Días de test (default: 7)
      --show-recommendations     Mostrar top-10 recommendations
      --verbose                  Logs detallados

   Ejemplos:
      $ python manage.py evaluate_model --model-path ml/models/dqn_agent.h5
      $ python manage.py evaluate_model --model-path ml/models/dqn_agent.h5 --show-recommendations


3️⃣  COLLECT_INTERACTIONS - Recopila y procesa interacciones
   └─ python manage.py collect_interactions [OPTIONS]

   Opciones:
      --days NUM              Días de interacciones (default: 7)
      --user-id ID           ID de usuario específico (opcional)
      --generate-report      Generar reporte en archivo
      --save-session         Guardar como sesión
      --verbose              Logs detallados

   Ejemplos:
      $ python manage.py collect_interactions --days 7
      $ python manage.py collect_interactions --user-id 1 --generate-report
      $ python manage.py collect_interactions --days 30 --save-session


4️⃣  SYNC_SPOTIFY_TRACKS - Sincroniza tracks desde Spotify
   └─ python manage.py sync_spotify_tracks [OPTIONS]

   Opciones:
      --user-id ID          ID del usuario a sincronizar (opcional)
      --playlist-id ID      ID de playlist de Spotify (opcional)
      --limit NUM           Límite de tracks (default: 50)
      --save-all            Guardar todos los tracks
      --verbose             Logs detallados

   Ejemplos:
      $ python manage.py sync_spotify_tracks
      $ python manage.py sync_spotify_tracks --user-id 1 --limit 100
      $ python manage.py sync_spotify_tracks --playlist-id spotify:playlist:123abc


📚 WORKFLOW RECOMENDADO:

   1. Entrena el agente:
      $ python manage.py train_agent --episodes 100 --days 30 --save

   2. Recopila interacciones:
      $ python manage.py collect_interactions --days 7 --save-session

   3. Evalúa el modelo:
      $ python manage.py evaluate_model --model-path ml/models/dqn_agent.h5

   4. Sincroniza tracks:
      $ python manage.py sync_spotify_tracks --limit 100


💡 TIPS:

   • Usa --verbose para debugging detallado
   • Los modelos se guardan en: ml/models/dqn_agent_YYYYMMDD_HHMMSS.h5
   • Los logs se guardan en: ml/logs/training_YYYYMMDD_HHMMSS.json
   • Los reportes se guardan en: interaction_report_YYYYMMDD_HHMMSS.txt


🔧 CONFIGURACIÓN REQUERIDA:

   • Base de datos PostgreSQL: Configurada ✅
   • Django settings: Configurados ✅
   • Spotify API: Requiere credenciales en .env
      SPOTIFY_CLIENT_ID=xxx
      SPOTIFY_CLIENT_SECRET=xxx


❓ PARA MÁS INFORMACIÓN:

   • Documentación: Ver DEVELOPMENT.md
   • Tests: python -m pytest ml/tests/ -v
   • Admin: http://localhost:8000/admin

╔════════════════════════════════════════════════════════════════════════════╗
║                        ¡Happy Experimenting! 🚀                           ║
╚════════════════════════════════════════════════════════════════════════════╝
"""

        if command:
            # Mostrar ayuda de comando específico
            self.stdout.write(f"\n📖 Ayuda para: {command}\n")
            self.stdout.write(f"Ejecuta: python manage.py {command} --help\n")
        else:
            # Mostrar ayuda general
            self.stdout.write(help_text)
