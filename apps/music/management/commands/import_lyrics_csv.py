"""
Importa letras desde spotify_millsongdata.csv a la BD.
Insercion rapida: almacena todas las letras como unmatched primero.
El matching fuzzy se hace en una segunda pasada o via comando separado.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.music.models import TrackLyrics

DATASETS_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "ml" / "datasets"
CHUNK_SIZE = 50000


class Command(BaseCommand):
    help = "Importa letras desde spotify_millsongdata.csv (fast bulk insert)"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=0, help="Limitar filas (0 = todo)")
        parser.add_argument("--chunk-size", type=int, default=CHUNK_SIZE)

    def handle(self, *args, **options):
        path = DATASETS_DIR / "spotify_millsongdata.csv"
        if not path.exists():
            self.stdout.write(self.style.ERROR(f"No encontrado: {path}"))
            return

        limit = options["limit"]
        chunk_size = options["chunk_size"]

        total = 0
        total_errors = 0
        lyrics_batch = []

        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if limit and total >= limit:
                    break

                try:
                    csv_artist = str(row.get("artist", "")).strip()
                    csv_song = str(row.get("song", "")).strip()
                    text = str(row.get("text", ""))

                    if not csv_artist or not csv_song or not text or text == "nan":
                        continue

                    word_count = len(text.split())

                    lyrics_batch.append(
                        TrackLyrics(
                            track_id=None,
                            artist_name=csv_artist[:255],
                            song_name=csv_song[:255],
                            text=text,
                            language="",
                            word_count=word_count,
                            match_score=None,
                            match_status="unmatched",
                        )
                    )

                except Exception as e:
                    total_errors += 1
                    if total_errors <= 5:
                        self.stdout.write(self.style.WARNING(f"Error en fila: {e}"))

                total += 1

                if len(lyrics_batch) >= chunk_size:
                    self._flush(lyrics_batch)
                    self.stdout.write(f"  {total:,} importados...")
                    lyrics_batch = []

        if lyrics_batch:
            self._flush(lyrics_batch)

        self.stdout.write(
            self.style.SUCCESS(
                f"Letras importadas: {total:,} registros, {total_errors} errores"
            )
        )

    def _flush(self, batch):
        with transaction.atomic():
            TrackLyrics.objects.bulk_create(batch, ignore_conflicts=True, batch_size=len(batch))
