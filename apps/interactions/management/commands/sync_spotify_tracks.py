"""
Comando: uv run manage.py sync_spotify_tracks

Sincroniza tracks desde la API de Spotify con la base de datos local.

Ejemplos:
    uv run manage.py sync_spotify_tracks --user-id 1 --liked
    uv run manage.py sync_spotify_tracks --user-id 1 --top
    uv run manage.py sync_spotify_tracks --playlist-id 3cEYpDpmLSvzlEecCXqDsF
    uv run manage.py sync_spotify_tracks --user-id 1 --limit 100 --save-audio-features
"""

import logging

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.music.services.music_data_service import MusicDataService
from apps.music.services.spotify_music_service import SpotifyMusicService

User = get_user_model()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Sincroniza tracks desde Spotify API con la BD local"

    def add_arguments(self, parser):
        parser.add_argument(
            "--user-id",
            type=int,
            default=None,
            help="ID del usuario Django a sincronizar",
        )
        parser.add_argument(
            "--playlist-id",
            type=str,
            default=None,
            help="ID de la playlist de Spotify a sincronizar",
        )
        parser.add_argument(
            "--liked",
            action="store_true",
            help="Sincronizar canciones que le gustan al usuario",
        )
        parser.add_argument(
            "--top",
            action="store_true",
            help="Sincronizar top tracks del usuario",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=50,
            help="Número máximo de tracks a sincronizar (default: 50)",
        )
        parser.add_argument(
            "--save-audio-features",
            action="store_true",
            help="Guardar características de audio para cada track",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Mostrar logs detallados",
        )

    def handle(self, *args, **options):
        user_id = options["user_id"]
        playlist_id = options["playlist_id"]
        limit = options["limit"]
        save_audio_features = options["save_audio_features"]
        verbose = options["verbose"]
        liked = options["liked"]
        top = options["top"]

        # Configurar logging
        log_level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(level=log_level)

        self.stdout.write(
            self.style.SUCCESS("\n[SYNC] Sincronizando tracks de Spotify")
        )

        try:
            # Determinar el usuario a usar
            if playlist_id and not user_id:
                # Para playlists públicas, necesitamos un usuario para autenticarse
                # Usamos el primer usuario disponible con conexión a Spotify
                user = User.objects.filter(is_spotify_connected=True).first()
                if not user:
                    raise CommandError(
                        "Se necesita al menos un usuario conectado a Spotify para sincronizar playlists"
                    )
            elif user_id:
                try:
                    user = User.objects.get(id=user_id)
                    if not user.is_spotify_connected:
                        raise CommandError(
                            f"Usuario {user.username} no está conectado a Spotify"
                        )
                except User.DoesNotExist as e:
                    raise CommandError(f"Usuario {user_id} no existe") from e
            else:
                raise CommandError("Debes especificar --user-id, --playlist-id o ambos")

            # Inicializar servicio de Spotify
            spotify_service = SpotifyMusicService(user)
            if not spotify_service.client:
                raise CommandError(
                    f"No se pudo autenticar con Spotify para usuario {user.username}"
                )

            # 1. Obtener tracks
            self.stdout.write(
                self.style.SUCCESS("\n[FETCH] Buscando tracks en Spotify...")
            )
            tracks = []

            if playlist_id:
                self.stdout.write(f"   Fuente: Playlist {playlist_id[:20]}...")
                tracks = spotify_service.get_playlist_tracks(
                    playlist_id=playlist_id, limit=limit
                )
            elif liked:
                self.stdout.write(f"   Fuente: Liked Songs de {user.username}")
                tracks = spotify_service.get_user_liked_tracks(limit=limit)
            elif top:
                self.stdout.write(f"   Fuente: Top tracks de {user.username}")
                tracks = spotify_service.get_top_tracks(limit=limit)
            else:
                # Default: liked tracks
                self.stdout.write(
                    f"   Fuente: Liked Songs de {user.username} (default)"
                )
                tracks = spotify_service.get_user_liked_tracks(limit=limit)

            if not tracks:
                self.stdout.write(
                    self.style.WARNING("   [WARN] No se encontraron tracks")
                )
                return

            self.stdout.write(
                self.style.SUCCESS(f"   [OK] {len(tracks)} tracks encontrados")
            )

            # 2. Guardar tracks en BD
            self.stdout.write(
                self.style.SUCCESS("\n[SAVE] Guardando tracks en base de datos...")
            )

            # Obtener audio features si se solicita
            audio_features_data = None
            if save_audio_features:
                self.stdout.write("   [FETCH] Obteniendo características de audio...")
                track_ids = [t.get("id") for t in tracks if t.get("id")]
                if track_ids:
                    audio_features_data = spotify_service.get_audio_features(track_ids)

            saved_count, skipped_count = MusicDataService.persist_tracks(
                tracks_data=tracks,
                save_audio_features=save_audio_features,
                audio_features_data=audio_features_data,
            )

            self.stdout.write(
                self.style.SUCCESS(f"\n   [OK] {saved_count} tracks nuevos guardados")
            )
            if skipped_count > 0:
                self.stdout.write(
                    self.style.NOTICE(f"   [INFO] {skipped_count} tracks ya existían")
                )

            # 4. Mostrar resumen final
            self.stdout.write(
                f"\n[SUMMARY]"
                f"\n   Total procesados: {len(tracks)}"
                f"\n   Nuevos tracks: {saved_count}"
                f"\n   Tracks existentes: {skipped_count}"
                f"\n   Fuente: {'Playlist' if playlist_id else ('Liked Songs' if liked else ('Top Tracks' if top else 'Default'))}"
            )

            self.stdout.write(
                self.style.SUCCESS("[OK] Sincronización completada exitosamente!\n")
            )

        except CommandError:
            raise
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"\n[ERROR] Error durante la sincronización:\n{e!s}\n")
            )
            if verbose:
                import traceback

                traceback.print_exc()
            raise CommandError(str(e)) from e
