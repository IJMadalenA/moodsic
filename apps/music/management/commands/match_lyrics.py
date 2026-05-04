"""
Vincula TrackLyrics unmatched a Tracks usando exact match + fuzzy con pre-filtro
por artista. Solo procesa registros con track__isnull=True.
"""

from __future__ import annotations

import re
from collections import defaultdict

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

    def handle(self, *args, **options):
        if not RAPIDFUZZ_AVAILABLE:
            self.stdout.write(self.style.ERROR("rapidfuzz no instalado"))
            return

        unmatched_count = TrackLyrics.objects.filter(track__isnull=True).count()
        self.stdout.write(f"Letras sin vincular: {unmatched_count:,}")

        if unmatched_count == 0:
            self.stdout.write("Nada que vincular.")
            return

        self.stdout.write("Construyendo indices...")
        exact_index: dict[str, int] = {}
        artist_index: dict[str, list[tuple[int, str]]] = defaultdict(list)

        for tid, tname in Track.objects.values_list("id", "name").iterator(chunk_size=10000):
            if tname:
                norm = _normalize(tname)
                if norm:
                    exact_index[norm] = tid

        for tid, tname, aname in Track.objects.values_list(
            "id", "name", "artists__name"
        ).iterator(chunk_size=10000):
            if tname and aname:
                norm_artist = _normalize(aname)
                artist_index[norm_artist].append((tid, _normalize(tname)))

        self.stdout.write(f"  Exact index: {len(exact_index):,} canciones")
        self.stdout.write(f"  Artist index: {len(artist_index):,} artistas")

        exact_matched = 0
        fuzzy_matched = 0
        fuzzy_reviewed = 0
        still_unmatched = 0
        processed = 0
        lyrics_to_update = []

        for lyric in TrackLyrics.objects.filter(track__isnull=True).iterator(
            chunk_size=CHUNK_SIZE
        ):
            processed += 1
            norm_song = _normalize(lyric.song_name)
            norm_artist = _normalize(lyric.artist_name)
            best_track_id = None
            best_score = 0

            if norm_song in exact_index:
                best_track_id = exact_index[norm_song]
                best_score = 100
                exact_matched += 1
            elif norm_artist in artist_index:
                candidates = artist_index[norm_artist]
                if candidates:
                    songs_in_artist = [name for _, name in candidates]
                    ids_in_artist = [tid for tid, _ in candidates]
                    result = process.extractOne(
                        norm_song,
                        songs_in_artist,
                        scorer=fuzz.token_sort_ratio,
                        score_cutoff=MATCH_THRESHOLD_LOW,
                    )
                    if result:
                        _, best_score, matched_idx = result
                        best_track_id = ids_in_artist[matched_idx]

            if not best_track_id and exact_index:
                all_songs = list(exact_index.keys())
                all_ids = list(exact_index.values())
                result = process.extractOne(
                    norm_song,
                    all_songs,
                    scorer=fuzz.token_sort_ratio,
                    score_cutoff=MATCH_THRESHOLD_HIGH,
                )
                if result:
                    _, best_score, matched_idx = result
                    best_track_id = all_ids[matched_idx]

            if best_track_id:
                if best_score >= MATCH_THRESHOLD_HIGH:
                    lyric.track_id = best_track_id
                    lyric.match_score = best_score
                    lyric.match_status = "matched"
                    if best_score < 100:
                        fuzzy_matched += 1
                else:
                    lyric.track_id = best_track_id
                    lyric.match_score = best_score
                    lyric.match_status = "reviewed"
                    fuzzy_reviewed += 1
            else:
                still_unmatched += 1

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
