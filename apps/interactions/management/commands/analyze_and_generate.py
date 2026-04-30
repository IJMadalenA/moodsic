"""
Comando: manage.py analyze_and_generate

Analiza hasta 500 canciones del historial de Spotify del usuario
(liked tracks, top tracks, listas recientes) y genera una playlist
personalizada de N canciones usando el agente RL de MoodSic.

Ejemplos:
    manage.py analyze_and_generate --username anaramosluna
    manage.py analyze_and_generate --username anaramosluna --count 35
    manage.py analyze_and_generate --username anaramosluna --count 35 --name "Mi Mix Moodsic"
    manage.py analyze_and_generate --username anaramosluna --max-tracks 500 --count 35
    manage.py analyze_and_generate --username anaramosluna --dry-run
"""

import logging

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()


class Command(BaseCommand):
    help = "Analiza el historial de Spotify y genera una playlist personalizada"

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            type=str,
            required=True,
            help="Nombre de usuario de MoodSic cuyo historial analizar",
        )
        parser.add_argument(
            "--max-tracks",
            type=int,
            default=500,
            help="Número máximo de canciones a analizar desde Spotify (default: 500)",
        )
        parser.add_argument(
            "--count",
            type=int,
            default=35,
            help="Número de canciones en la playlist generada (default: 35)",
        )
        parser.add_argument(
            "--name",
            type=str,
            default=None,
            help="Nombre de la playlist (default: 'MoodSic Mix · <fecha>')",
        )
        parser.add_argument(
            "--include-playlists",
            type=int,
            default=5,
            metavar="N",
            help="Número de playlists propias a incluir en el análisis (default: 5, 0=desactivar)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo analiza y muestra estadísticas sin crear la playlist",
        )

    def handle(self, *args, **options):
        from django.utils import timezone
        from apps.music.services.spotify_music_service import SpotifyMusicService
        from apps.music.services.music_data_service import MusicDataService
        from apps.interactions.services.playlist_generation_service import (
            get_playlist_generation_service,
        )

        username = options["username"]
        max_tracks = options["max_tracks"]
        count = options["count"]
        playlist_name = options["name"] or f"MoodSic Mix · {timezone.now().strftime('%d %b %Y')}"
        include_playlists = options["include_playlists"]
        dry_run = options["dry_run"]

        # --- 1. Obtener usuario ---
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"Usuario '{username}' no encontrado.")

        if not user.is_spotify_connected:
            raise CommandError(
                f"El usuario '{username}' no tiene Spotify conectado. "
                "Inicia sesión con Spotify primero."
            )

        self.stdout.write(self.style.SUCCESS(f"\n🎵 MoodSic · Análisis para @{username}"))
        self.stdout.write(f"   Objetivo: analizar hasta {max_tracks} canciones → generar {count} canciones\n")

        # --- 2. Inicializar cliente Spotify ---
        self.stdout.write("🔗 Conectando con Spotify...")
        spotify = SpotifyMusicService(user)
        if not spotify.client:
            raise CommandError(
                "No se pudo conectar con Spotify. El token puede haber expirado. "
                "Vuelve a iniciar sesión en /accounts/spotify/login/."
            )
        user_info = spotify.get_user_info()
        spotify_display = user_info.get("display_name", username) if user_info else username
        self.stdout.write(self.style.SUCCESS(f"   ✅ Conectado como: {spotify_display}"))

        # --- 3. Recopilar canciones de múltiples fuentes ---
        all_tracks_data: list[dict] = []
        seen_ids: set[str] = set()

        def add_tracks(tracks: list[dict], source: str):
            before = len(all_tracks_data)
            for t in tracks:
                tid = t.get("id")
                if tid and tid not in seen_ids:
                    seen_ids.add(tid)
                    all_tracks_data.append(t)
            added = len(all_tracks_data) - before
            self.stdout.write(f"   + {added:>3} canciones únicas  ←  {source}")

        # Liked tracks (paginado, hasta max_tracks)
        self.stdout.write("\n📥 Recopilando historial de Spotify...")
        liked = spotify.get_user_liked_tracks_paginated(max_tracks=max_tracks)
        add_tracks(liked, f"Liked Tracks (total: {len(liked)})")

        # Top tracks en tres períodos de tiempo
        for time_range, label in [
            ("short_term", "Top Tracks · últimas 4 semanas"),
            ("medium_term", "Top Tracks · últimos 6 meses"),
            ("long_term", "Top Tracks · histórico"),
        ]:
            if len(all_tracks_data) >= max_tracks:
                break
            top = spotify.get_top_tracks(limit=50, time_range=time_range)
            add_tracks(top, label)

        # Historial reciente
        if len(all_tracks_data) < max_tracks:
            recent = spotify.get_recently_played(limit=50)
            add_tracks(recent, "Historial reciente (Recently Played)")

        # Playlists propias
        if include_playlists > 0 and len(all_tracks_data) < max_tracks:
            self.stdout.write(f"\n📂 Analizando tus playlists (hasta {include_playlists})...")
            playlists = spotify.get_user_playlists(limit=include_playlists + 10)
            own_playlists = [
                p for p in playlists
                if p.get("owner", {}).get("id") == (user_info or {}).get("id")
            ][:include_playlists]

            for pl in own_playlists:
                if len(all_tracks_data) >= max_tracks:
                    break
                pl_name = pl.get("name", "?")
                pl_id = pl.get("id")
                pl_tracks = spotify.get_tracks_from_playlist(pl_id, limit=100)
                add_tracks(pl_tracks, f"Playlist: «{pl_name}»")

        total_collected = len(all_tracks_data)
        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ Total canciones únicas recopiladas: {total_collected}"
            )
        )

        if total_collected == 0:
            raise CommandError("No se encontraron canciones en el historial de Spotify.")

        # Limitar al objetivo
        tracks_to_import = all_tracks_data[:max_tracks]

        # --- 4. Guardar en BD local ---
        self.stdout.write(f"\n💾 Importando {len(tracks_to_import)} canciones a la BD local...")
        saved, skipped = MusicDataService.persist_tracks(tracks_to_import)
        self.stdout.write(
            f"   Nuevas: {saved} | Ya existían: {skipped} | "
            f"Total en BD: {saved + skipped}"
        )

        # --- 4b. Importar Audio Features reales desde Spotify ---
        # Las audio features (energía, bailable, valencia, etc.) son esenciales
        # para que el agente RL tome decisiones informadas sobre cada canción.
        self.stdout.write("\n🎛️  Importando audio features desde Spotify...")
        from apps.music.models import Track, TrackAudioFeatures

        track_ids_without_features = list(
            Track.objects.filter(
                spotify_id__in=[t.get("id") for t in tracks_to_import if t.get("id")],
                audio_features__isnull=True,
            ).values_list("spotify_id", flat=True)[:500]
        )

        features_saved = 0
        if track_ids_without_features:
            try:
                audio_features_map = spotify.get_audio_features(track_ids_without_features)
                for spotify_id, feat in audio_features_map.items():
                    if not feat:
                        continue
                    try:
                        track_obj = Track.objects.get(spotify_id=spotify_id)
                        TrackAudioFeatures.objects.update_or_create(
                            track=track_obj,
                            defaults={
                                "danceability": feat.get("danceability") or 0.0,
                                "energy": feat.get("energy") or 0.0,
                                "key": feat.get("key") or 0,
                                "loudness": feat.get("loudness") or 0.0,
                                "mode": feat.get("mode") or 0,
                                "speechiness": feat.get("speechiness") or 0.0,
                                "acousticness": feat.get("acousticness") or 0.0,
                                "instrumentalness": feat.get("instrumentalness") or 0.0,
                                "liveness": feat.get("liveness") or 0.0,
                                "valence": feat.get("valence") or 0.0,
                                "tempo": feat.get("tempo") or 0.0,
                                "time_signature": feat.get("time_signature") or 4,
                            },
                        )
                        features_saved += 1
                    except Track.DoesNotExist:
                        pass
                if features_saved > 0:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"   ✅ Audio features reales guardadas: {features_saved}/{len(track_ids_without_features)} tracks"
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            "   ⚠️  AVISO: Spotify devolvió 0 audio features (API /audio-features deprecada "
                            "para apps no aprobadas desde Nov 2024). El agente RL usará valores neutros (0.5) "
                            "para las características de audio de cada canción."
                        )
                    )
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"   ⚠️  No se pudieron obtener audio features: {e}"))
        else:
            already_have = TrackAudioFeatures.objects.filter(
                track__spotify_id__in=[t.get("id") for t in tracks_to_import if t.get("id")]
            ).count()
            self.stdout.write(f"   ℹ️  Todos los tracks ya tienen audio features ({already_have} en BD)")

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"\n⚠️  --dry-run activado: análisis completado, "
                    f"no se generó playlist."
                )
            )
            self.stdout.write(f"   Ejecuta sin --dry-run para generar la playlist de {count} canciones.")
            return

        # --- 5. Obtener contexto de clima REAL desde la BD ---
        # El agente RL necesita el WeatherContext para personalizar la selección.
        # Si no hay datos recientes (>60 min), forzar refresh desde Open-Meteo.
        from apps.context.models import WeatherContext as WeatherContextModel
        from apps.context.services.weather_service import WeatherService
        from apps.context.management.commands.refresh_context import _StubCity

        weather_context_dict = None
        latest_wc = WeatherContextModel.objects.order_by("-timestamp").first()
        max_age_minutes = 60

        if latest_wc:
            age_min = (timezone.now() - latest_wc.timestamp).total_seconds() / 60
            if age_min > max_age_minutes:
                self.stdout.write(f"\n🌤  Clima en BD tiene {age_min:.0f} min → refrescando desde Open-Meteo...")
                try:
                    stub = _StubCity("Madrid", "ES", 40.4168, -3.7038)
                    latest_wc = WeatherService.fetch_and_store_weather(stub)
                    self.stdout.write(f"   ✅ Clima actualizado: {latest_wc.temperature}°C, {latest_wc.description}")
                except Exception as exc:
                    self.stdout.write(self.style.WARNING(f"   ⚠️  No se pudo refrescar clima: {exc}"))
        else:
            self.stdout.write("\n🌤  No hay clima en BD → obteniendo de Open-Meteo...")
            try:
                stub = _StubCity("Madrid", "ES", 40.4168, -3.7038)
                latest_wc = WeatherService.fetch_and_store_weather(stub)
                self.stdout.write(f"   ✅ Clima obtenido: {latest_wc.temperature}°C, {latest_wc.description}")
            except Exception as exc:
                self.stdout.write(self.style.WARNING(f"   ⚠️  No se pudo obtener clima: {exc}"))

        if latest_wc:
            weather_context_dict = {
                "temperature": latest_wc.temperature or 20.0,
                "feels_like": latest_wc.feels_like or latest_wc.temperature or 20.0,
                "humidity": latest_wc.humidity or 60,
                "wind_speed": latest_wc.wind_speed or 0.0,
                "pressure": latest_wc.pressure or 1013,
                "visibility": latest_wc.visibility or 10000,
                "clouds_all": latest_wc.clouds_all if latest_wc.clouds_all is not None else 50,
                "rain_probability": latest_wc.rain_1h or 0,
                "main_status": latest_wc.main_status or "",
            }
            self.stdout.write(
                f"   Clima real usado: {latest_wc.temperature}°C, "
                f"{latest_wc.humidity}% hum, {latest_wc.main_status}"
            )
        else:
            self.stdout.write(
                self.style.WARNING("   ⚠️  AVISO: Agente RL usará valores de clima por defecto (sin API real)")
            )

        # --- 6. Generar playlist con el agente RL ---
        self.stdout.write(
            f"\n🤖 Generando playlist «{playlist_name}» con {count} canciones..."
        )
        self.stdout.write("   (Agente RL analizando contexto + historial del usuario)")

        service = get_playlist_generation_service()
        result = service.generate_playlist(
            user=user,
            playlist_name=playlist_name,
            count=count,
            use_context=True,
            weather_context=weather_context_dict,
        )

        # --- 6. Mostrar resultados ---
        self.stdout.write(self.style.SUCCESS("\n🎧 Playlist generada:"))
        self.stdout.write(f"   Nombre:    {result['playlist_name']}")
        self.stdout.write(f"   Canciones: {result['tracks_count']}")

        duration_min = result["estimated_duration"] // 60
        duration_sec = result["estimated_duration"] % 60
        self.stdout.write(f"   Duración:  ~{duration_min}m {duration_sec:02d}s")

        if result.get("playlist_id") and not result["playlist_id"].startswith("moodsic_"):
            self.stdout.write(
                self.style.SUCCESS(
                    f"   Spotify ID: {result['playlist_id']}"
                )
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"   🔗 https://open.spotify.com/playlist/{result['playlist_id']}"
                )
            )
        else:
            self.stdout.write("   (Playlist guardada localmente, no sincronizada con Spotify)")

        self.stdout.write("\n   Canciones seleccionadas:")
        for i, name in enumerate(result["track_names"], 1):
            self.stdout.write(f"   {i:>2}. {name}")

        mode_icons = {
            "online": "🌐 Online (Spotify)",
            "offline": "📴 Offline (BD local)",
            "hybrid": "🔀 Híbrido",
        }
        mode = result.get("mode", "?")
        self.stdout.write(
            f"\n   Modo: {mode_icons.get(mode, mode)}"
        )
        self.stdout.write(
            self.style.SUCCESS("\n✅ ¡Todo listo! Abre Spotify para escuchar tu playlist.\n")
        )
