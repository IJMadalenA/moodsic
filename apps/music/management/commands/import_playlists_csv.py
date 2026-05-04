"""Importa playlists desde final_playlists.csv y mapeos de genero desde playlists.csv."""

from __future__ import annotations

import csv
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.music.models import Playlist, PlaylistGenre

DATASETS_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "ml" / "datasets"


def _extract_playlist_id(uri: str) -> str:
    if "spotify:playlist:" in uri:
        return uri.split("spotify:playlist:")[1]
    if "open.spotify.com/playlist/" in uri:
        return uri.split("/playlist/")[1].split("?")[0]
    return uri


class Command(BaseCommand):
    help = "Importa playlists desde final_playlists.csv y playlists.csv"

    def handle(self, *args, **options):
        pl_path = DATASETS_DIR / "playlists" / "final_playlists.csv"
        if pl_path.exists():
            self.stdout.write(f"Importando playlists desde {pl_path.name}...")
            created = 0
            with open(pl_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    uri = row.get("uri", "")
                    pl_id = _extract_playlist_id(uri)
                    if not pl_id:
                        continue
                    _, was_created = Playlist.objects.get_or_create(
                        spotify_id=pl_id,
                        defaults={
                            "uri": uri,
                            "name": (row.get("name") or "")[:255],
                            "description": (row.get("description") or "")[:500],
                            "is_public": True,
                        },
                    )
                    if was_created:
                        created += 1
            self.stdout.write(f"  Playlists: {created} creadas")

        map_path = DATASETS_DIR / "playlists" / "playlists.csv"
        if map_path.exists():
            self.stdout.write(f"Importando generos de playlists desde {map_path.name}...")
            created = 0
            with open(map_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    pl_id = row.get("Playlist", "").strip()
                    genre = row.get("Genre", "").strip()
                    if not pl_id or not genre:
                        continue
                    playlist = Playlist.objects.filter(spotify_id=pl_id).first()
                    if playlist:
                        _, was_created = PlaylistGenre.objects.get_or_create(
                            playlist=playlist,
                            genre=genre,
                        )
                        if was_created:
                            created += 1
            self.stdout.write(f"  Generos: {created} creados")

        self.stdout.write(self.style.SUCCESS(f"Total playlists: {Playlist.objects.count():,}"))
