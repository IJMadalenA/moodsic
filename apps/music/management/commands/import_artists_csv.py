"""Importa artistas desde artists.csv a la BD."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.music.models import Artist

DATASETS_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "ml" / "datasets"


def _extract_artist_id(uri: str) -> str:
    if "spotify:artist:" in uri:
        return uri.split("spotify:artist:")[1]
    return uri


def _parse_genres(raw: str):
    if not raw or raw == "[]":
        return []
    try:
        parsed = json.loads(raw.replace("'", '"'))
        return parsed if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


class Command(BaseCommand):
    help = "Importa artistas desde artists.csv"

    def handle(self, *args, **options):
        path = DATASETS_DIR / "artists.csv"
        if not path.exists():
            self.stdout.write(self.style.ERROR(f"No encontrado: {path}"))
            return

        self.stdout.write(f"Importando artistas desde {path.name}...")

        created = 0
        updated = 0
        errors = 0

        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    artist_id = _extract_artist_id(row.get("artist_uri", ""))
                    if not artist_id:
                        continue

                    genres = _parse_genres(row.get("artist_genres", "[]"))
                    popularity = row.get("artist_popularity")
                    followers = row.get("artist_followers")

                    obj, was_created = Artist.objects.update_or_create(
                        spotify_id=artist_id,
                        defaults={
                            "uri": row.get("artist_uri", ""),
                            "popularity": int(popularity) if popularity and popularity.isdigit() else None,
                            "genres": genres,
                        },
                    )
                    if was_created:
                        created += 1
                    else:
                        updated += 1
                except Exception as e:
                    errors += 1
                    if errors <= 5:
                        self.stdout.write(self.style.WARNING(f"Error en fila: {e}"))

        self.stdout.write(
            self.style.SUCCESS(f"Artistas: {created} creados, {updated} actualizados, {errors} errores")
        )
