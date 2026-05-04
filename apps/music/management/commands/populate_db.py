import spotipy
from django.conf import settings
from django.core.management.base import BaseCommand
from spotipy.oauth2 import SpotifyClientCredentials

from apps.music.models import Album, Artist, Track, TrackAudioFeatures


class Command(BaseCommand):
    help = "Carga datos detallados de Spotify"

    def handle(self, *args, **kwargs):
        self.stdout.write("Conectando con Spotify...")

        # Limpiamos las credenciales de posibles espacios o errores de formato
        try:
            conf = settings.SOCIALACCOUNT_PROVIDERS["spotify"]["APP"]
            client_id = str(conf["client_id"]).strip()
            client_secret = str(conf["secret"]).strip()

            auth_manager = SpotifyClientCredentials(
                client_id=client_id, client_secret=client_secret
            )
            sp = spotipy.Spotify(auth_manager=auth_manager)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error en credenciales: {e}"))
            return

        # --- 1. CARGAR ARTISTAS ---
        self.stdout.write("Cargando artistas...")
        try:
            # ELIMINAMOS limit y offset PARA EVITAR EL ERROR 400
            res = sp.search(q="genre:pop", type="artist")
            for a in res["artists"]["items"]:
                Artist.objects.update_or_create(
                    spotify_id=a["id"],
                    defaults={
                        "name": a["name"],
                        "popularity": a.get("popularity"),
                        "genres": a.get("genres", []),
                        "images": a.get("images", []),
                        "uri": a.get("uri", ""),
                    },
                )
            self.stdout.write(
                self.style.SUCCESS(f"Artistas cargados: {len(res['artists']['items'])}")
            )
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Error en artistas: {e}"))

        # --- 2. CARGAR ÁLBUMES ---
        self.stdout.write("Cargando álbumes...")
        try:
            res = sp.search(q="year:2025", type="album")
            for alb in res["albums"]["items"]:
                album_obj, _ = Album.objects.update_or_create(
                    spotify_id=alb["id"],
                    defaults={
                        "name": alb["name"],
                        "album_type": alb.get("album_type", ""),
                        "total_tracks": alb.get("total_tracks"),
                        "release_date": alb.get("release_date", ""),
                        "images": alb.get("images", []),
                        "uri": alb.get("uri", ""),
                    },
                )
            self.stdout.write(
                self.style.SUCCESS(f"Álbumes cargados: {len(res['albums']['items'])}")
            )
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Error en álbumes: {e}"))

        # --- 3. CARGAR MUCHAS CANCIONES ---
        # --- 3. CARGAR MUCHAS CANCIONES (VERSIÓN MASIVA) ---
        self.stdout.write("Cargando lote masivo de canciones...")

        # Ampliamos la lista de géneros para diversificar los resultados
        busquedas = [
            "pop 2026",
            "rock 80s",
            "heavy metal",
            "jazz classics",
            "hip hop 2025",
            "electro house",
            "reggaeton 2026",
            "indie rock",
            "blues",
            "classical music",
            "k-pop",
            "lofi beats",
            "country music",
            "disco hits",
            "synthwave",
            "punk rock",
            "salsa classics",
            "techno underground",
            "r&b soul",
            "folk",
        ]

        for query in busquedas:
            self.stdout.write(f"Buscando: {query}...")
            try:
                # Mantenemos la llamada limpia sin limit/offset para evitar el error 400
                results = sp.search(query, type="track")

                if "tracks" in results and "items" in results["tracks"]:
                    tracks = results["tracks"]["items"]

                    for t in tracks:
                        try:
                            # 1. Guardar canción básica
                            track_obj, created = Track.objects.update_or_create(
                                spotify_id=t["id"],
                                defaults={
                                    "name": t["name"],
                                    "duration_ms": t["duration_ms"],
                                    "explicit": t["explicit"],
                                    "popularity": t.get("popularity", 0),
                                    "preview_url": t.get("preview_url") or "",
                                    "track_number": t["track_number"],
                                    "uri": t.get("uri", ""),
                                },
                            )

                            # 2. Artistas
                            for art_data in t["artists"]:
                                artist_obj, _ = Artist.objects.get_or_create(
                                    spotify_id=art_data["id"],
                                    defaults={
                                        "name": art_data["name"],
                                        "uri": art_data.get("uri", ""),
                                    },
                                )
                                track_obj.artists.add(artist_obj)

                            # 3. Álbum
                            if t["album"]:
                                alb_obj, _ = Album.objects.get_or_create(
                                    spotify_id=t["album"]["id"],
                                    defaults={
                                        "name": t["album"]["name"],
                                        "images": t["album"].get("images", []),
                                        "release_date": t["album"].get(
                                            "release_date", ""
                                        ),
                                    },
                                )
                                track_obj.album = alb_obj
                                track_obj.save()

                        except Exception as exc:
                            self.stdout.write(self.style.WARNING(f"Error al procesar canción {t.get('id', 'N/A')}: {exc}"))

                    self.stdout.write(
                        self.style.SUCCESS(f"Añadidas canciones de: {query}")
                    )

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Fallo en {query}: {e}"))

        total = Track.objects.count()
        self.stdout.write(
            self.style.SUCCESS(
                f"¡LOGRADO! Ahora tienes {total} canciones en tu base de datos."
            )
        )
