"""
Importa letras desde spotify_millsongdata.csv usando fuzzy matching contra la BD.

Estrategia:
1. Pre-carga todos los (track_id, track_name) de la BD
2. Para cada fila del CSV, busca el mejor match con rapidfuzz
3. score >= 85: match_status=matched, track FK asignado
4. 70 <= score < 85: match_status=reviewed
5. score < 70: match_status=unmatched
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.music.models import Track, TrackLyrics

try:
    from rapidfuzz import fuzz, process

    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False

try:
    from langdetect import DetectorFactory, detect

    DetectorFactory.seed = 0
    HAS_LANGDETECT = True
except ImportError:
    HAS_LANGDETECT = False

DATASETS_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "ml" / "datasets"
CHUNK_SIZE = 50000
MATCH_THRESHOLD_HIGH = 85
MATCH_THRESHOLD_LOW = 70


def _clean_name(name: str) -> str:
    name = str(name).lower().strip()
    name = re.sub(r"\(feat\..*?\)", "", name)
    name = re.sub(r"\(ft\..*?\)", "", name)
    name = re.sub(r"\[.*?\]", "", name)
    name = re.sub(r"\(.*?\)", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


class Command(BaseCommand):
    help = "Importa letras desde spotify_millsongdata.csv con fuzzy matching"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=0, help="Limitar filas a procesar (0 = todo)")
        parser.add_argument("--chunk-size", type=int, default=CHUNK_SIZE)

    def handle(self, *args, **options):
        if not RAPIDFUZZ_AVAILABLE:
            self.stdout.write(self.style.ERROR("rapidfuzz no instalado. pip install rapidfuzz"))
            return

        path = DATASETS_DIR / "spotify_millsongdata.csv"
        if not path.exists():
            self.stdout.write(self.style.ERROR(f"No encontrado: {path}"))
            return

        limit = options["limit"]
        chunk_size = options["chunk_size"]

        self.stdout.write("Construyendo indice de tracks desde la BD...")
        track_index = []
        for t in Track.objects.values_list("id", "name", flat=False).iterator(chunk_size=5000):
            track_index.append((t[0], _clean_name(t[1])))
        self.stdout.write(f"  Indice: {len(track_index):,} tracks")

        song_names_only = [name for _, name in track_index]
        track_ids_only = [tid for tid, _ in track_index]

        total_matched = 0
        total_reviewed = 0
        total_unmatched = 0
        total_errors = 0
        processed = 0
        lyrics_batch = []

        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if limit and processed >= limit:
                    break

                try:
                    csv_artist = str(row.get("artist", "")).strip()
                    csv_song = str(row.get("song", "")).strip()
                    text = str(row.get("text", ""))

                    if not csv_artist or not csv_song or not text or text == "nan":
                        continue

                    clean_song = _clean_name(csv_song)

                    best_match = None
                    best_score = 0
                    best_track_id = None

                    if song_names_only:
                        result = process.extractOne(
                            clean_song,
                            song_names_only,
                            scorer=fuzz.token_sort_ratio,
                            score_cutoff=MATCH_THRESHOLD_LOW,
                        )
                        if result:
                            matched_name, best_score, matched_idx = result
                            best_track_id = track_ids_only[matched_idx]

                    match_status = "unmatched"
                    if best_score >= MATCH_THRESHOLD_HIGH and best_track_id:
                        match_status = "matched"
                        total_matched += 1
                    elif best_score >= MATCH_THRESHOLD_LOW and best_track_id:
                        match_status = "reviewed"
                        total_reviewed += 1
                    else:
                        match_status = "unmatched"
                        best_track_id = None
                        total_unmatched += 1

                    language = ""
                    if HAS_LANGDETECT and len(text) > 30:
                        try:
                            sample = text[:200]
                            language = detect(sample)
                        except Exception:
                            language = ""

                    word_count = len(text.split())

                    lyrics_batch.append(
                        TrackLyrics(
                            track_id=best_track_id,
                            artist_name=csv_artist[:255],
                            song_name=csv_song[:255],
                            text=text,
                            language=language,
                            word_count=word_count,
                            match_score=best_score if best_score else None,
                            match_status=match_status,
                        )
                    )

                except Exception as e:
                    total_errors += 1
                    if total_errors <= 5:
                        self.stdout.write(self.style.WARNING(f"Error en fila: {e}"))

                processed += 1

                if len(lyrics_batch) >= chunk_size:
                    self._flush(lyrics_batch)
                    self.stdout.write(
                        f"  {processed:,} procesados | matched={total_matched:,} "
                        f"reviewed={total_reviewed:,} unmatched={total_unmatched:,}"
                    )
                    lyrics_batch = []

        if lyrics_batch:
            self._flush(lyrics_batch)

        self.stdout.write(
            self.style.SUCCESS(
                f"Letras importadas: {total_matched:,} matched, "
                f"{total_reviewed:,} reviewed, {total_unmatched:,} unmatched, "
                f"{total_errors} errores"
            )
        )

    def _flush(self, batch):
        with transaction.atomic():
            TrackLyrics.objects.bulk_create(batch, ignore_conflicts=True, batch_size=len(batch))
