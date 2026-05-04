"""
Vincula TrackLyrics unmatched a Tracks usando exact match + fuzzy global.
Optimizado: sin indice de artista (M2M lento con 1.16M tracks).
"""

from __future__ import annotations

import re

from django.core.management.base import BaseCommand

from apps.music.models import Track, TrackLyrics

try:
    from rapidfuzz import fuzz, process

    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False

CHUNK_SIZE = 1000
MATCH_THRESHOLD_HIGH = 85
MATCH_THRESHOLD_LOW = 75


def _normalize(text: str) -> str:
    t = str(text).lower().strip()
    t = re.sub(r"\(feat\..*?\)", "", t)
    t = re.sub(r"\(ft\..*?\)", "", t)
    t = re.sub(r"\[.*?\]", "", t)
    t = re.sub(r"\(.*?\)", "", t)
    t = re.sub(r"['\u2018\u2019\u201c\u201d]", "", t)
    t = re.sub(r"[^a-z0-9\s]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


class Command(BaseCommand):
    help = "Vincula TrackLyrics unmatched a Tracks via exact + fuzzy matching"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=0, help="Limitar a N letras")
        parser.add_argument("--exact-only", action="store_true", help="Solo exact match, sin fuzzy")

    def handle(self, *args, **options):
        if not RAPIDFUZZ_AVAILABLE:
            self.stdout.write(self.style.ERROR("rapidfuzz no instalado"))
            return

        limit = options["limit"]
        exact_only = options["exact_only"]

        unmatched_count = TrackLyrics.objects.filter(track__isnull=True).count()
        self.stdout.write(f"Letras sin vincular: {unmatched_count:,}")

        if unmatched_count == 0:
            self.stdout.write("Nada que vincular.")
            return

        self.stdout.write("Construyendo indice de canciones...")
        exact_index: dict[str, int] = {}
        for tid, tname in Track.objects.values_list("id", "name").iterator(chunk_size=10000):
            if tname:
                norm = _normalize(tname)
                if norm:
                    exact_index[norm] = tid
        self.stdout.write(f"  Indice: {len(exact_index):,} canciones unicas")

        if not exact_only:
            names_list = list(exact_index.keys())
            ids_list = list(exact_index.values())

        exact_matched = 0
        fuzzy_matched = 0
        fuzzy_reviewed = 0
        still_unmatched = 0
        processed = 0
        lyrics_to_update = []

        qs = TrackLyrics.objects.filter(track__isnull=True)
        if limit:
            qs = qs[:limit]

        for lyric in qs.iterator(chunk_size=CHUNK_SIZE):
            processed += 1
            norm_song = _normalize(lyric.song_name)
            best_track_id = None
            best_score = 0

            # Fase 1: exact match
            if norm_song in exact_index:
                best_track_id = exact_index[norm_song]
                best_score = 100
                exact_matched += 1

            # Fase 2: fuzzy match global
            elif not exact_only and names_list:
                result = process.extractOne(
                    norm_song,
                    names_list,
                    scorer=fuzz.token_sort_ratio,
                    score_cutoff=MATCH_THRESHOLD_LOW,
                )
                if result:
                    _, best_score, matched_idx = result
                    best_track_id = ids_list[matched_idx]
                    if best_score >= MATCH_THRESHOLD_HIGH:
                        fuzzy_matched += 1
                    else:
                        fuzzy_reviewed += 1
                else:
                    still_unmatched += 1
            else:
                still_unmatched += 1

            if best_track_id:
                lyric.track_id = best_track_id
                lyric.match_score = best_score
                lyric.match_status = "matched" if best_score >= MATCH_THRESHOLD_HIGH else "reviewed"

            lyrics_to_update.append(lyric)

            if len(lyrics_to_update) >= CHUNK_SIZE:
                self._flush(lyrics_to_update)
                self.stdout.write(
                    f"  {processed:,} | exact={exact_matched:,} "
                    f"fuzzy={fuzzy_matched:,} reviewed={fuzzy_reviewed:,} "
                    f"unmatched={still_unmatched:,}"
                )
                lyrics_to_update = []

        if lyrics_to_update:
            self._flush(lyrics_to_update)

        self.stdout.write(
            self.style.SUCCESS(
                f"Vinculacion: {exact_matched + fuzzy_matched:,} matched "
                f"({exact_matched:,} exact, {fuzzy_matched:,} fuzzy), "
                f"{fuzzy_reviewed:,} reviewed, {still_unmatched:,} unmatched"
            )
        )

    def _flush(self, batch):
        TrackLyrics.objects.bulk_update(batch, ["track", "match_score", "match_status"])
