"""Importa tracks y audio features desde unified_tracks.csv a la BD."""

from __future__ import annotations

import csv
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.music.models import Track, TrackAudioFeatures

DATASETS_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "ml" / "datasets"
BATCH_SIZE = 5000
AUDIO_FEATURE_COLS = [
    "danceability",
    "energy",
    "key",
    "loudness",
    "mode",
    "speechiness",
    "acousticness",
    "instrumentalness",
    "liveness",
    "valence",
    "tempo",
    "time_signature",
]


def _safe_float(val, default=None):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _safe_int(val, default=None):
    try:
        return int(float(val))
    except (TypeError, ValueError):
        return default


def _safe_bool(val, default=False):
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().lower() in ("true", "1", "yes")
    return default


class Command(BaseCommand):
    help = "Importa tracks desde unified_tracks.csv"

    def add_arguments(self, parser):
        parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
        parser.add_argument("--skip-existing", action="store_true", help="Skip tracks that already exist")

    def handle(self, *args, **options):
        path = DATASETS_DIR / "unified_tracks.csv"
        if not path.exists():
            self.stdout.write(self.style.ERROR(f"No encontrado: {path}. Ejecuta 'unify_csvs' primero."))
            return

        batch_size = options["batch_size"]
        skip_existing = options["skip_existing"]

        self.stdout.write(f"Importando tracks desde {path.name}...")

        tracks_batch = []
        features_batch = []
        total_created = 0
        total_skipped = 0
        total_errors = 0

        existing_ids = set()
        if skip_existing:
            existing_ids = set(Track.objects.values_list("spotify_id", flat=True))
            self.stdout.write(f"  {len(existing_ids):,} tracks existentes en BD (skip mode)")

        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                track_id = row.get("track_id", "")
                if not track_id:
                    continue
                if skip_existing and track_id in existing_ids:
                    total_skipped += 1
                    continue

                try:
                    is_playable = _safe_bool(row.get("is_playable"), True)
                    explicit = _safe_bool(row.get("explicit"), False)

                    subgenre = row.get("playlist_subgenre") or row.get("subgenre") or ""
                    analysis_url = row.get("analysis_url") or ""

                    track = Track(
                        spotify_id=track_id,
                        name=(row.get("name") or "")[:255],
                        duration_ms=_safe_int(row.get("duration_ms"), 0),
                        explicit=explicit,
                        popularity=_safe_int(row.get("popularity")),
                        track_number=_safe_int(row.get("track_number"), 1),
                        genre=(row.get("genre") or "")[:100],
                        subgenre=subgenre[:100],
                        is_playable=is_playable,
                        analysis_url=analysis_url[:500],
                    )
                    tracks_batch.append(track)

                    feature_data = {}
                    for col in AUDIO_FEATURE_COLS:
                        val = row.get(col)
                        if val is not None and val != "":
                            feature_data[col] = _safe_float(val)

                    if feature_data:
                        features_batch.append((track_id, feature_data))

                except Exception as e:
                    total_errors += 1
                    if total_errors <= 5:
                        self.stdout.write(self.style.WARNING(f"Error parseando fila {i}: {e}"))

                if len(tracks_batch) >= batch_size:
                    created, errs = self._flush_batch(tracks_batch, features_batch)
                    total_created += created
                    total_errors += errs
                    tracks_batch = []
                    features_batch = []
                    self.stdout.write(f"  Progreso: {total_created + total_skipped:,} procesados...")

        if tracks_batch:
            created, errs = self._flush_batch(tracks_batch, features_batch)
            total_created += created
            total_errors += errs

        self.stdout.write(
            self.style.SUCCESS(f"Tracks: {total_created} creados, {total_skipped} saltados, {total_errors} errores")
        )

    def _flush_batch(self, tracks_batch: list, features_batch: list) -> tuple[int, int]:
        with transaction.atomic():
            created_tracks = Track.objects.bulk_create(
                tracks_batch,
                ignore_conflicts=True,
                batch_size=len(tracks_batch),
            )

            track_ids_in_batch = {t.spotify_id for t in tracks_batch}
            created_map = {t.spotify_id: t for t in Track.objects.filter(spotify_id__in=track_ids_in_batch)}

            features_to_create = []
            for track_id, feat_data in features_batch:
                if track_id in created_map:
                    track_obj = created_map[track_id]
                    try:
                        features_to_create.append(TrackAudioFeatures(track=track_obj, **feat_data))
                    except Exception:
                        pass

            if features_to_create:
                TrackAudioFeatures.objects.bulk_create(features_to_create, ignore_conflicts=True)

        return len(tracks_batch), 0
