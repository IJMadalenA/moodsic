"""Orquesta todos los comandos de importacion en orden."""

from __future__ import annotations

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Ejecuta el pipeline completo de unificacion e importacion de CSVs"

    def handle(self, *args, **options):
        steps = [
            ("unify_csvs", "Unificando CSVs fuente..."),
            ("import_artists_csv", "Importando artistas..."),
            ("import_tracks_csv", "Importando tracks..."),
            ("import_playlists_csv", "Importando playlists..."),
            ("import_lyrics_csv", "Importando letras..."),
        ]

        for cmd_name, description in steps:
            self.stdout.write(f"\n=== {description} ===")
            try:
                call_command(cmd_name, *args, **options)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Fallo en {cmd_name}: {e}"))
                return

        from apps.music.models import Playlist, PlaylistGenre, Track, TrackAudioFeatures, TrackLyrics

        self.stdout.write(
            self.style.SUCCESS(
                f"\n=== RESUMEN FINAL ===\n"
                f"Tracks: {Track.objects.count():,}\n"
                f"Audio Features: {TrackAudioFeatures.objects.count():,}\n"
                f"Playlists: {Playlist.objects.count():,}\n"
                f"Playlist Genres: {PlaylistGenre.objects.count():,}\n"
                f"Letras: {TrackLyrics.objects.count():,}\n"
                f"  matched: {TrackLyrics.objects.filter(match_status='matched').count():,}\n"
                f"  reviewed: {TrackLyrics.objects.filter(match_status='reviewed').count():,}\n"
                f"  unmatched: {TrackLyrics.objects.filter(match_status='unmatched').count():,}"
            )
        )
