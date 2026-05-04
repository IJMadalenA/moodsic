"""Analiza el sentimiento de las letras usando VADER."""

from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.music.models import TrackLyrics
from apps.music.services.lyrics_service import get_lyrics_nlp_service

CHUNK_SIZE = 1000


class Command(BaseCommand):
    help = "Analiza el sentimiento de TrackLyrics con VADER"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=0, help="Limitar procesamiento")
        parser.add_argument("--force", action="store_true", help="Re-analizar ya analizados")

    def handle(self, *args, **options):
        svc = get_lyrics_nlp_service()
        limit = options["limit"]
        force = options["force"]

        qs = TrackLyrics.objects.filter(text__isnull=False).exclude(text="")
        if not force:
            qs = qs.filter(sentiment_score__isnull=True)
        total = qs.count()
        self.stdout.write(f"Letras pendientes de analisis: {total:,}")

        if total == 0:
            self.stdout.write("Nada que analizar.")
            return

        positive = 0
        negative = 0
        neutral = 0
        processed = 0
        lyrics_to_update = []

        for lyric in qs.iterator(chunk_size=CHUNK_SIZE):
            if limit and processed >= limit:
                break

            try:
                result = svc.analyze(lyric.text)
                lyric.sentiment_score = result["sentiment_score"]
                lyric.sentiment_label = result["sentiment_label"]
                lyric.sentiment_pos = result["sentiment_pos"]
                lyric.sentiment_neg = result["sentiment_neg"]
                lyric.sentiment_neu = result["sentiment_neu"]
                lyrics_to_update.append(lyric)

                if result["sentiment_label"] == "positive":
                    positive += 1
                elif result["sentiment_label"] == "negative":
                    negative += 1
                else:
                    neutral += 1
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Error: {e}"))

            processed += 1

            if len(lyrics_to_update) >= CHUNK_SIZE:
                self._flush(lyrics_to_update)
                self.stdout.write(
                    f"  {processed:,} | pos={positive:,} neg={negative:,} neu={neutral:,}"
                )
                lyrics_to_update = []

        if lyrics_to_update:
            self._flush(lyrics_to_update)

        self.stdout.write(
            self.style.SUCCESS(
                f"Analisis: {positive:,} positive, {negative:,} negative, {neutral:,} neutral"
            )
        )

    def _flush(self, batch):
        TrackLyrics.objects.bulk_update(
            batch,
            [
                "sentiment_score",
                "sentiment_label",
                "sentiment_pos",
                "sentiment_neg",
                "sentiment_neu",
            ],
        )
