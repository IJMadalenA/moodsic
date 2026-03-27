"""
Comando: python manage.py collect_interactions

Recopila y procesa interacciones del usuario, calculando métricas agregadas.

Ejemplos:
    python manage.py collect_interactions
    python manage.py collect_interactions --days 7
    python manage.py collect_interactions --days 30 --user-id 1
    python manage.py collect_interactions --generate-report
"""

import logging
from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.interactions.models import Interaction, InteractionSession

User = get_user_model()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Recopila y procesa interacciones del usuario del sistema"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=7,
            help="Número de días de interacciones a procesar (default: 7)",
        )
        parser.add_argument(
            "--user-id",
            type=int,
            default=None,
            help="ID del usuario específico a procesar (opcional)",
        )
        parser.add_argument(
            "--generate-report",
            action="store_true",
            help="Generar reporte de estadísticas",
        )
        parser.add_argument(
            "--save-session",
            action="store_true",
            help="Guardar interacciones en una nueva sesión",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Mostrar logs detallados",
        )

    def handle(self, *args, **options):
        days = options["days"]
        user_id = options["user_id"]
        generate_report = options["generate_report"]
        save_session = options["save_session"]
        verbose = options["verbose"]

        # Configurar logging
        log_level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(level=log_level)

        self.stdout.write(self.style.SUCCESS(f"\n📊 Recopilando interacciones"))
        self.stdout.write(f"   📅 Últimos {days} días")

        try:
            # 1. Filtrar interacciones
            self.stdout.write("\n🔍 Buscando interacciones...")
            cutoff_date = timezone.now() - timedelta(days=days)

            query = Interaction.objects.filter(started_at__gte=cutoff_date).order_by("-started_at")

            if user_id:
                query = query.filter(user_id=user_id)
                user_name = User.objects.get(id=user_id).username
                self.stdout.write(f"   Usuario: {user_name}")

            interactions = list(query)
            self.stdout.write(
                self.style.SUCCESS(f"   ✅ {len(interactions)} interacciones encontradas")
            )

            if not interactions:
                self.stdout.write(
                    self.style.WARNING("   ⚠️  No hay interacciones para procesar")
                )
                return

            # 2. Calcular estadísticas
            self.stdout.write("\n📈 Procesando estadísticas...")

            stats = self._calculate_stats(interactions)

            self.stdout.write(self.style.SUCCESS("   ✅ Estadísticas calculadas"))

            # 3. Mostrar resumen
            self.stdout.write(
                f"\n📊 Resumen de Interacciones:\n"
                f"   Total: {stats['total']}\n"
                f"   Completadas: {stats['completed']} ({stats['completion_rate']:.1f}%)\n"
                f"   Skipped: {stats['skipped']} ({stats['skip_rate']:.1f}%)\n"
                f"   Reward promedio: {stats['avg_reward']:.4f}\n"
                f"   Usuarios únicos: {stats['unique_users']}\n"
                f"   Tracks únicos: {stats['unique_tracks']}"
            )

            # 4. Mostrar top tracks
            self.stdout.write(f"\n🎵 Top 5 Tracks más reproducidos:")
            for i, (track_id, count) in enumerate(stats["top_tracks"][:5], 1):
                self.stdout.write(f"   {i}. Track ID: {track_id} ({count} veces)")

            # 5. Guardar sesión si aplica
            if save_session:
                self.stdout.write("\n💾 Guardando sesión...")
                session = self._create_session(interactions)
                self.stdout.write(
                    self.style.SUCCESS(f"   ✅ Sesión creada: {session.id}")
                )

            # 6. Generar reporte si aplica
            if generate_report:
                self.stdout.write("\n📄 Generando reporte...")
                self._generate_report(interactions, stats)
                self.stdout.write(self.style.SUCCESS("   ✅ Reporte generado"))

            self.stdout.write(
                self.style.SUCCESS("\n✅ Recopilación completada exitosamente!\n")
            )

        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"\n❌ Usuario no encontrado: {user_id}\n"))
            raise CommandError(f"Usuario {user_id} no existe")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n❌ Error al recopilar:\n{str(e)}\n"))
            raise CommandError(str(e))

    def _calculate_stats(self, interactions):
        """Calcula estadísticas de las interacciones."""
        from collections import Counter

        total = len(interactions)
        completed = sum(1 for i in interactions if i.feedback == "completed")
        skipped = sum(1 for i in interactions if i.feedback in ["skip", "skip_immediate"])

        rewards = [i.reward for i in interactions if i.reward]
        avg_reward = sum(rewards) / len(rewards) if rewards else 0

        users = set(i.user_id for i in interactions)
        tracks = set(i.track_id for i in interactions)

        track_counts = Counter(i.track_id for i in interactions)

        return {
            "total": total,
            "completed": completed,
            "skipped": skipped,
            "completion_rate": (completed / total * 100) if total > 0 else 0,
            "skip_rate": (skipped / total * 100) if total > 0 else 0,
            "avg_reward": avg_reward,
            "unique_users": len(users),
            "unique_tracks": len(tracks),
            "top_tracks": track_counts.most_common(),
        }

    def _create_session(self, interactions):
        """Crea una sesión de interacciones."""
        # Usar el usuario de la primera interacción
        user = interactions[0].user if interactions else None

        session = InteractionSession.objects.create(
            user=user,
        )

        # Vincular interacciones a la sesión
        Interaction.objects.filter(id__in=[i.id for i in interactions]).update(
            session=session
        )

        return session

    def _generate_report(self, interactions, stats):
        """Genera un reporte de interacciones."""
        filename = f"interaction_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

        with open(filename, "w") as f:
            f.write("=" * 60 + "\n")
            f.write("📊 REPORTE DE INTERACCIONES\n")
            f.write("=" * 60 + "\n\n")

            f.write(f"Fecha de generación: {datetime.now()}\n")
            f.write(f"Total de interacciones: {stats['total']}\n")
            f.write(f"Completadas: {stats['completed']} ({stats['completion_rate']:.1f}%)\n")
            f.write(f"Skipped: {stats['skipped']} ({stats['skip_rate']:.1f}%)\n")
            f.write(f"Reward promedio: {stats['avg_reward']:.4f}\n")
            f.write(f"Usuarios únicos: {stats['unique_users']}\n")
            f.write(f"Tracks únicos: {stats['unique_tracks']}\n\n")

            f.write("Top 10 Tracks:\n")
            for i, (track_id, count) in enumerate(stats["top_tracks"][:10], 1):
                f.write(f"  {i}. Track {track_id}: {count} veces\n")

        self.stdout.write(f"   Reporte guardado: {filename}")
