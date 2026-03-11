from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Automatiza la configuración inicial de los datos geográficos de cities_light."
    )

    def handle(self, *_args, **_options):
        self.stdout.write("--- Configuración de Datos Geográficos (cities_light) ---")

        # 1. Aplicar migraciones necesarias si las hubiera
        self.stdout.write("Verificando migraciones...")
        call_command("migrate", "cities_light", interactive=False)
        self.stdout.write(self.style.SUCCESS("✓ Migraciones de cities_light al día."))

        # 2. Población de datos
        self.stdout.write(
            "Poblando datos geográficos (esto puede tardar varios minutos)..."
        )
        try:
            # El comando 'cities_light' ya es idempotente (actualiza lo que existe)
            call_command("cities_light")
            self.stdout.write(
                self.style.SUCCESS(
                    "✓ Población de datos geográficos completada con éxito."
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"✘ Error durante la población de datos: {e!s}")
            )
            return

        self.stdout.write("---------------------------------------------------------")
