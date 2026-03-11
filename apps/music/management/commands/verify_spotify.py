from django.conf import settings
from django.core.management.base import BaseCommand

from apps.music.services.spotify_music_service import SpotifyMusicService


class Command(BaseCommand):
    help = "Verifica el estado de la API de Spotify y las credenciales configuradas."

    def handle(self, *_args, **_options):
        self.stdout.write("--- Verificación de Spotify API ---")

        # 1. Verificar credenciales en settings
        client_id = getattr(settings, "SPOTIPY_CLIENT_ID", None)
        client_secret = getattr(settings, "SPOTIPY_CLIENT_SECRET", None)
        redirect_uri = getattr(settings, "SPOTIPY_REDIRECT_URI", None)

        if not all([client_id, client_secret, redirect_uri]):
            self.stdout.write(
                self.style.ERROR(
                    "✘ Faltan credenciales de Spotify en settings.py o .env"
                )
            )
            self.stdout.write(
                f"  SPOTIPY_CLIENT_ID: {'CONFIGURADO' if client_id else 'FALTA'}"
            )
            self.stdout.write(
                f"  SPOTIPY_CLIENT_SECRET: {'CONFIGURADO' if client_secret else 'FALTA'}"
            )
            self.stdout.write(
                f"  SPOTIPY_REDIRECT_URI: {'CONFIGURADO' if redirect_uri else 'FALTA'}"
            )
            return

        self.stdout.write(
            self.style.SUCCESS("✓ Credenciales presentes en la configuración.")
        )

        # 2. Verificar conexión con la API (Client Credentials Flow)
        self.stdout.write("Probando conexión con Spotify API...")
        success, message = SpotifyMusicService.verify_api_connection()

        if success:
            self.stdout.write(self.style.SUCCESS(f"✓ {message}"))
        else:
            self.stdout.write(self.style.ERROR(f"✘ {message}"))

        self.stdout.write("------------------------------------")
