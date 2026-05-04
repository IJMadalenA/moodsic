# NLP sobre Letras y Ponderación por Ánimo — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Vincular las 59K letras restantes a tracks, enriquecer TrackLyrics con features de NLP (VADER sentiment + emociones), e integrar un `lyrics_mood_score` en el RewardCalculator para que el agente RL pondere canciones por el ánimo de su letra.

**Architecture:** Tres fases incrementales. Fase 1 (matching eficiente con dict + fuzzy). Fase 2 (modelo TrackLyrics expandido + comando `analyze_lyrics` con VADER). Fase 3 (nuevo método `_calculate_lyrics_mood_reward` en RewardCalculator, hook en RewardService para pasar lyrics al calculator, integración opcional con MoodService para mood contextual).

**Tech Stack:** Python 3.12, Django 5.2, vaderSentiment, rapidfuzz (ya instalado), numpy (ya instalado)

---

## File Structure

```
Files to CREATE:
  apps/music/management/commands/match_lyrics.py
  apps/music/management/commands/analyze_lyrics.py
  apps/music/services/lyrics_service.py
  apps/music/tests/test_lyrics_matching.py
  apps/music/tests/test_lyrics_nlp.py
  ml/tests/test_lyrics_mood_reward.py

Files to MODIFY:
  apps/music/models/tracklyrics.py              (add sentiment/emotion fields)
  ml/reward.py                                  (add _calculate_lyrics_mood_reward, new weight)
  apps/interactions/services/reward_service.py  (fetch lyrics data, pass to calculator)
  requirements.txt                              (add vaderSentiment)
```

---

## FASE 1: Vinculación completa de letras

### Task 1.1: Instalar dependencias NLP

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Install vaderSentiment**

```bash
/home/ijmadalena/PycharmProjects/moodsic/.venv/bin/pip install vaderSentiment
```

Expected: `Successfully installed vaderSentiment-...`

- [ ] **Step 2: Add to requirements.txt**

Append to `requirements.txt` after the `tqdm` line in the CSV Unification section:

```
vaderSentiment
```

- [ ] **Step 3: Verify import works**

```bash
/home/ijmadalena/PycharmProjects/moodsic/.venv/bin/python3 -c "from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer; analyzer = SentimentIntensityAnalyzer(); print(analyzer.polarity_scores('I love this song, it makes me so happy and alive!'))"
```

Expected: `{'neg': 0.0, 'neu': 0.426, 'pos': 0.574, 'compound': 0.9062}`

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "chore: add vaderSentiment for lyrics NLP analysis"
```

---

### Task 1.2: Comando `match_lyrics` (vinculación completa)

**Files:**
- Create: `apps/music/management/commands/match_lyrics.py`
- Test: `apps/music/tests/test_lyrics_matching.py`

El comando toma todas las `TrackLyrics` con `track__isnull=True` y las vincula a tracks usando:
1. Dict de match exacto (nombre de canción normalizado → track.id)
2. Fuzzy match con pre-filtro por artista (solo sobre las que no tuvieron exact match)

- [ ] **Step 1: Write the failing test**

`apps/music/tests/test_lyrics_matching.py`:

```python
from django.core.management import call_command

from apps.music.models import Track, TrackLyrics


class TestMatchLyricsCommand:
    def test_exact_match(self, db):
        track = Track.objects.create(
            spotify_id="s1", name="Hello", duration_ms=200000, track_number=1
        )
        lyric = TrackLyrics.objects.create(
            artist_name="Adele",
            song_name="Hello",
            text="Hello from the other side",
            match_status="unmatched",
        )
        call_command("match_lyrics")
        lyric.refresh_from_db()
        assert lyric.match_status == "matched"
        assert lyric.track == track
        assert lyric.match_score == 100

    def test_fuzzy_match(self, db):
        track = Track.objects.create(
            spotify_id="s2", name="Hello", duration_ms=200000, track_number=1
        )
        lyric = TrackLyrics.objects.create(
            artist_name="Adele",
            song_name="Hello (Live)",
            text="Hello from the other side",
            match_status="unmatched",
        )
        call_command("match_lyrics")
        lyric.refresh_from_db()
        assert lyric.match_status in ("matched", "reviewed")
        assert lyric.track == track

    def test_no_match_remains_unmatched(self, db):
        track = Track.objects.create(
            spotify_id="s3", name="Unique Song XYZ", duration_ms=200000, track_number=1
        )
        lyric = TrackLyrics.objects.create(
            artist_name="Unknown",
            song_name="Nonexistent Song",
            text="la la la",
            match_status="unmatched",
        )
        call_command("match_lyrics")
        lyric.refresh_from_db()
        assert lyric.match_status == "unmatched"

    def test_already_matched_not_modified(self, db):
        track = Track.objects.create(
            spotify_id="s4", name="Old Song", duration_ms=200000, track_number=1
        )
        lyric = TrackLyrics.objects.create(
            artist_name="A",
            song_name="Old Song",
            text="x",
            match_status="matched",
            match_score=95,
            track=track,
        )
        call_command("match_lyrics")
        lyric.refresh_from_db()
        assert lyric.match_status == "matched"
        assert lyric.match_score == 95  # unchanged
```

- [ ] **Step 2: Run test to verify it fails**

```bash
/home/ijmadalena/PycharmProjects/moodsic/.venv/bin/python3 -m pytest apps/music/tests/test_lyrics_matching.py -v
```

Expected: FAIL - `No module named 'apps.music.management.commands.match_lyrics'` or similar

- [ ] **Step 3: Write match_lyrics command**

`apps/music/management/commands/match_lyrics.py`:

```python
"""
Vincula TrackLyrics unmatched a Tracks usando exact match + fuzzy con pre-filtro
por artista. Solo procesa registros con track__isnull=True.
"""

from __future__ import annotations

import re
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

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

        for lyric in TrackLyrics.objects.filter(track__isnull=True).iterator(chunk_size=CHUNK_SIZE):
            processed += 1
            norm_song = _normalize(lyric.song_name)
            norm_artist = _normalize(lyric.artist_name)
            best_track_id = None
            best_score = 0

            # Fase 1: exact match por nombre de cancion
            if norm_song in exact_index:
                best_track_id = exact_index[norm_song]
                best_score = 100
                exact_matched += 1
            # Fase 2: fuzzy match pre-filtrado por artista
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

            # Fase 3: fuzzy match global (solo si no hay match por artista)
            if not best_track_id:
                all_songs = list(exact_index.keys())
                all_ids = list(exact_index.values())
                if all_songs:
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
                    if best_score == 100:
                        pass  # ya contado como exact
                    else:
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
```

- [ ] **Step 4: Run test to verify it passes**

```bash
/home/ijmadalena/PycharmProjects/moodsic/.venv/bin/python3 -m pytest apps/music/tests/test_lyrics_matching.py -v
```

Expected: ALL 4 tests PASS

- [ ] **Step 5: Clean and run on real data**

First, reset any previously matched lyrics (from the 1000-row test) back to unmatched so we get a clean run:

```bash
/home/ijmadalena/PycharmProjects/moodsic/.venv/bin/python3 manage.py shell -c "
from apps.music.models import TrackLyrics
TrackLyrics.objects.all().update(track=None, match_score=None, match_status='unmatched')
print('Reset done')
"
```

Then run matching:

```bash
/home/ijmadalena/PycharmProjects/moodsic/.venv/bin/python3 manage.py match_lyrics
```

Expected: ~14K-25K matched, ~3K reviewed, ~30K-45K unmatched

- [ ] **Step 8: Commit**

```bash
git add apps/music/management/commands/match_lyrics.py apps/music/tests/test_lyrics_matching.py
git commit -m "feat: add match_lyrics command with exact+fuzzy matching to link TrackLyrics to Tracks"
```

---

## FASE 2: NLP enrichment (VADER sentiment)

### Task 2.1: Expandir modelo TrackLyrics con campos NLP

**Files:**
- Modify: `apps/music/models/tracklyrics.py`

- [ ] **Step 1: Add NLP fields to TrackLyrics**

Add after `match_status` in `apps/music/models/tracklyrics.py`:

```python
    sentiment_score = models.FloatField(
        null=True, blank=True, verbose_name=_("Sentiment compound")
    )
    sentiment_label = models.CharField(
        max_length=20,
        blank=True,
        default="",
        verbose_name=_("Sentiment label"),
    )
    sentiment_pos = models.FloatField(
        null=True, blank=True, verbose_name=_("Positivity score")
    )
    sentiment_neg = models.FloatField(
        null=True, blank=True, verbose_name=_("Negativity score")
    )
    sentiment_neu = models.FloatField(
        null=True, blank=True, verbose_name=_("Neutrality score")
    )
```

- [ ] **Step 2: Generate and apply migration**

```bash
/home/ijmadalena/PycharmProjects/moodsic/.venv/bin/python3 manage.py makemigrations music
/home/ijmadalena/PycharmProjects/moodsic/.venv/bin/python3 manage.py migrate music
```

- [ ] **Step 3: Update model __str__ if needed** (no changes needed)

- [ ] **Step 4: Run existing tests to verify nothing broke**

```bash
/home/ijmadalena/PycharmProjects/moodsic/.venv/bin/python3 -m pytest apps/music/tests/test_tracklyrics_model.py apps/music/tests/test_lyrics_matching.py -v
```

Expected: All existing tests pass

- [ ] **Step 5: Commit**

```bash
git add apps/music/models/tracklyrics.py apps/music/migrations/
git commit -m "feat: add sentiment fields (VADER) to TrackLyrics model"
```

---

### Task 2.2: Lyrics NLP Service

**Files:**
- Create: `apps/music/services/lyrics_service.py`

- [ ] **Step 1: Write LyricsNLPService**

`apps/music/services/lyrics_service.py`:

```python
"""Servicio de NLP para analizar sentimiento de letras usando VADER."""

from __future__ import annotations

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


class LyricsNLPService:
    def __init__(self):
        self.analyzer = SentimentIntensityAnalyzer()

    def analyze(self, text: str) -> dict:
        scores = self.analyzer.polarity_scores(text)
        compound = scores["compound"]
        if compound >= 0.05:
            label = "positive"
        elif compound <= -0.05:
            label = "negative"
        else:
            label = "neutral"
        return {
            "sentiment_score": compound,
            "sentiment_label": label,
            "sentiment_pos": scores["pos"],
            "sentiment_neg": scores["neg"],
            "sentiment_neu": scores["neu"],
        }

    def get_mood_score(self, text: str) -> float:
        """Returns a normalized mood score 0-1 based on lyric sentiment."""
        result = self.analyze(text)
        compound = result["sentiment_score"]
        return (compound + 1.0) / 2.0


_lyrics_nlp_service: LyricsNLPService | None = None


def get_lyrics_nlp_service() -> LyricsNLPService:
    global _lyrics_nlp_service
    if _lyrics_nlp_service is None:
        _lyrics_nlp_service = LyricsNLPService()
    return _lyrics_nlp_service
```

- [ ] **Step 2: Commit**

```bash
git add apps/music/services/lyrics_service.py
git commit -m "feat: add LyricsNLPService with VADER sentiment analysis"
```

---

### Task 2.3: Comando `analyze_lyrics` (NLP batch processing)

**Files:**
- Create: `apps/music/management/commands/analyze_lyrics.py`
- Test: `apps/music/tests/test_lyrics_nlp.py`

- [ ] **Step 1: Write test_lyrics_nlp.py**

```python
from django.core.management import call_command

from apps.music.models import Track, TrackLyrics
from apps.music.services.lyrics_service import get_lyrics_nlp_service


class TestLyricsNLPService:
    def test_positive_sentiment(self):
        svc = get_lyrics_nlp_service()
        result = svc.analyze("I love this beautiful amazing song forever!")
        assert result["sentiment_label"] == "positive"
        assert result["sentiment_score"] > 0.5

    def test_negative_sentiment(self):
        svc = get_lyrics_nlp_service()
        result = svc.analyze("I hate this terrible awful horrible pain sorrow")
        assert result["sentiment_label"] == "negative"
        assert result["sentiment_score"] < -0.3

    def test_neutral_sentiment(self):
        svc = get_lyrics_nlp_service()
        result = svc.analyze("The chair is brown and the table is round")
        assert result["sentiment_label"] == "neutral"

    def test_mood_score_normalized(self):
        svc = get_lyrics_nlp_service()
        positive = svc.get_mood_score("I love this happy joyful song")
        negative = svc.get_mood_score("I hate this sad miserable song")
        assert 0.0 <= positive <= 1.0
        assert 0.0 <= negative <= 1.0
        assert positive > negative


class TestAnalyzeLyricsCommand:
    def test_analyze_updates_lyrics(self, db):
        track = Track.objects.create(
            spotify_id="t_analyze", name="Happy Song", duration_ms=200000, track_number=1
        )
        lyric = TrackLyrics.objects.create(
            track=track,
            artist_name="Test",
            song_name="Happy Song",
            text="I am so happy and joyful and wonderful today",
            match_status="matched",
        )
        call_command("analyze_lyrics")
        lyric.refresh_from_db()
        assert lyric.sentiment_score is not None
        assert lyric.sentiment_label in ("positive", "negative", "neutral")
        assert lyric.sentiment_pos is not None
        assert lyric.sentiment_neg is not None
        assert lyric.sentiment_neu is not None

    def test_skips_already_analyzed(self, db):
        track = Track.objects.create(
            spotify_id="t_skip", name="X", duration_ms=1000, track_number=1
        )
        lyric = TrackLyrics.objects.create(
            track=track,
            artist_name="A",
            song_name="X",
            text="y",
            match_status="matched",
            sentiment_score=0.5,
            sentiment_label="positive",
            sentiment_pos=0.6,
            sentiment_neg=0.1,
            sentiment_neu=0.3,
        )
        call_command("analyze_lyrics")
        lyric.refresh_from_db()
        assert lyric.sentiment_score == 0.5  # unchanged
```

- [ ] **Step 2: Run test to verify it fails (service test will pass, command test will fail)**

```bash
/home/ijmadalena/PycharmProjects/moodsic/.venv/bin/python3 -m pytest apps/music/tests/test_lyrics_nlp.py::TestLyricsNLPService -v
```

Expected: PASS for service tests

```bash
/home/ijmadalena/PycharmProjects/moodsic/.venv/bin/python3 -m pytest apps/music/tests/test_lyrics_nlp.py::TestAnalyzeLyricsCommand -v
```

Expected: FAIL - command not found

- [ ] **Step 3: Write analyze_lyrics command**

`apps/music/management/commands/analyze_lyrics.py`:

```python
"""Analiza el sentimiento de las letras usando VADER."""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

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
            ["sentiment_score", "sentiment_label", "sentiment_pos", "sentiment_neg", "sentiment_neu"],
        )
```

- [ ] **Step 4: Run command test**

```bash
/home/ijmadalena/PycharmProjects/moodsic/.venv/bin/python3 -m pytest apps/music/tests/test_lyrics_nlp.py -v
```

Expected: ALL 7 tests PASS

- [ ] **Step 5: Run on real data**

```bash
/home/ijmadalena/PycharmProjects/moodsic/.venv/bin/python3 manage.py analyze_lyrics
```

Expected: ~73K analyzed with sentiment distribution (likely ~40% positive, ~30% negative, ~30% neutral for song lyrics)

- [ ] **Step 6: Verify results**

```bash
/home/ijmadalena/PycharmProjects/moodsic/.venv/bin/python3 manage.py shell -c "
from apps.music.models import TrackLyrics
total = TrackLyrics.objects.count()
analyzed = TrackLyrics.objects.filter(sentiment_score__isnull=False).count()
for lbl in ['positive', 'negative', 'neutral']:
    c = TrackLyrics.objects.filter(sentiment_label=lbl).count()
    print(f'  {lbl}: {c:,} ({c/total*100:.1f}%)')
print(f'Total analyzed: {analyzed:,}')
lyrics = TrackLyrics.objects.filter(sentiment_score__isnull=False).order_by('-sentiment_score')[:3]
for l in lyrics:
    print(f'  +{l.sentiment_score:.3f} \"{l.song_name}\" - {l.text[:60]}...')
lyrics = TrackLyrics.objects.filter(sentiment_score__isnull=False).order_by('sentiment_score')[:3]
for l in lyrics:
    print(f'  {l.sentiment_score:.3f} \"{l.song_name}\" - {l.text[:60]}...')
"
```

- [ ] **Step 7: Commit**

```bash
git add apps/music/management/commands/analyze_lyrics.py apps/music/tests/test_lyrics_nlp.py apps/music/services/lyrics_service.py
git commit -m "feat: add analyze_lyrics command and LyricsNLPService with VADER sentiment"
```

---

## FASE 3: Integración del lyrics mood score en el RL RewardCalculator

### Task 3.1: Agregar `_calculate_lyrics_mood_reward` al RewardCalculator

**Files:**
- Modify: `ml/reward.py`

- [ ] **Step 1: Write the failing test**

`ml/tests/test_lyrics_mood_reward.py`:

```python
from ml.reward import RewardCalculator


class TestLyricsMoodReward:
    def test_positive_lyrics_give_positive_reward(self):
        calculator = RewardCalculator()
        reward = calculator._calculate_lyrics_mood_reward({"lyrics_sentiment_score": 0.8})
        assert reward > 0

    def test_negative_lyrics_give_negative_reward(self):
        calculator = RewardCalculator()
        reward = calculator._calculate_lyrics_mood_reward({"lyrics_sentiment_score": -0.8})
        assert reward < 0

    def test_neutral_lyrics_give_near_zero(self):
        calculator = RewardCalculator()
        reward = calculator._calculate_lyrics_mood_reward({"lyrics_sentiment_score": 0.0})
        assert abs(reward) < 0.2

    def test_mood_weight_applied(self):
        calculator = RewardCalculator(lyrics_mood_weight=0.3)
        reward = calculator._calculate_lyrics_mood_reward({"lyrics_sentiment_score": 0.5})
        assert abs(reward) < 0.3

    def test_calculate_reward_includes_lyrics(self):
        calculator = RewardCalculator(lyrics_mood_weight=0.15)
        reward = calculator.calculate_reward(
            user_feedback="completed",
            track_audio_features={"energy": 0.5, "danceability": 0.5, "valence": 0.5},
            lyrics_data={"lyrics_sentiment_score": 0.9, "lyrics_sentiment_label": "positive"},
        )
        assert reward > 1.0  # base + completion + lyrics bonus

    def test_no_lyrics_no_effect(self):
        calculator = RewardCalculator()
        reward = calculator.calculate_reward(
            user_feedback="completed",
            track_audio_features={"energy": 0.5},
        )
        # Should not crash and should give standard completion reward
        assert reward == 2.0  # base 1.0 + completion 1.0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
/home/ijmadalena/PycharmProjects/moodsic/.venv/bin/python3 -m pytest ml/tests/test_lyrics_mood_reward.py -v
```

Expected: FAIL - `AttributeError: 'RewardCalculator' object has no attribute '_calculate_lyrics_mood_reward'`

- [ ] **Step 3: Add `lyrics_mood_weight` to constructor + `_calculate_lyrics_mood_reward` method**

In `ml/reward.py`, modify the `__init__` signature (line 22-28):

```python
    def __init__(
        self,
        base_reward: float = 1.0,
        skip_penalty: float = -1.0,
        completion_bonus: float = 1.0,
        context_weight: float = 0.2,
        audio_feature_weight: float = 0.15,
        lyrics_mood_weight: float = 0.1,
    ):
        self.base_reward = base_reward
        self.skip_penalty = skip_penalty
        self.completion_bonus = completion_bonus
        self.context_weight = context_weight
        self.audio_feature_weight = audio_feature_weight
        self.lyrics_mood_weight = lyrics_mood_weight
```

Modify the `calculate_reward` method signature (line 46-52):

```python
    def calculate_reward(
        self,
        user_feedback: str | None = None,
        weather_context: dict | None = None,
        track_audio_features: dict | None = None,
        user_history: dict | None = None,
        lyrics_data: dict | None = None,
    ) -> float:
```

Add after the consistency_reward block (after line 97, before the `return`):

```python
        # 5. Animo de la letra (NLP sentiment)
        if lyrics_data:
            lyrics_mood_reward = self._calculate_lyrics_mood_reward(lyrics_data)
            reward += lyrics_mood_reward * self.lyrics_mood_weight
```

Add the new method after `_calculate_consistency_reward` (before `normalize_reward`):

```python
    def _calculate_lyrics_mood_reward(self, lyrics_data: dict) -> float:
        """
        Calcula bonificacion basada en el sentimiento de la letra.

        Las letras positivas dan recompensa positiva (cancion motivadora).
        Las letras negativas dan recompensa ligeramente negativa o neutra
        (no siempre se penaliza; hay gente que disfruta musica triste).
        """
        sentiment_score = lyrics_data.get("lyrics_sentiment_score", 0.0)

        if sentiment_score > 0.3:
            return 0.3
        elif sentiment_score > 0.1:
            return 0.15
        elif sentiment_score < -0.3:
            return -0.1
        else:
            return 0.0
```

- [ ] **Step 4: Run test to verify it passes**

```bash
/home/ijmadalena/PycharmProjects/moodsic/.venv/bin/python3 -m pytest ml/tests/test_lyrics_mood_reward.py -v
```

Expected: ALL 6 tests PASS

- [ ] **Step 5: Run existing reward tests to verify no regression**

```bash
/home/ijmadalena/PycharmProjects/moodsic/.venv/bin/python3 -m pytest ml/tests/test_reward.py -v
```

Expected: ALL existing tests PASS

- [ ] **Step 6: Commit**

```bash
git add ml/reward.py ml/tests/test_lyrics_mood_reward.py
git commit -m "feat: add lyrics_mood_weight and _calculate_lyrics_mood_reward to RewardCalculator"
```

---

### Task 3.2: Hook lyrics data into RewardService

**Files:**
- Modify: `apps/interactions/services/reward_service.py`

- [ ] **Step 1: Add `_get_lyrics_data` method and hook it in**

Add this method to `RewardService` class (after `_get_track_audio_features`):

```python
    @staticmethod
    def _get_lyrics_data(track: Track) -> dict | None:
        lyrics = TrackLyrics.objects.filter(
            track=track, sentiment_score__isnull=False
        ).order_by("-match_score").first()
        if not lyrics:
            return None
        return {
            "lyrics_sentiment_score": lyrics.sentiment_score,
            "lyrics_sentiment_label": lyrics.sentiment_label,
        }
```

Add at top of file imports:

```python
from apps.music.models import TrackLyrics
```

Modify `calculate_interaction_reward` (around line 46) to include lyrics:

```python
        lyrics_data = self._get_lyrics_data(track)

        raw_reward = self.reward_calculator.calculate_reward(
            user_feedback=user_feedback,
            weather_context=weather_context,
            track_audio_features=audio_features,
            user_history=history,
            lyrics_data=lyrics_data,
        )
```

- [ ] **Step 2: Commit**

```bash
git add apps/interactions/services/reward_service.py
git commit -m "feat: hook lyrics sentiment data into RewardService for RL agent"
```

---

### Task 3.3: Full integration test + verify pipeline

- [ ] **Step 1: Run the full test suite**

```bash
/home/ijmadalena/PycharmProjects/moodsic/.venv/bin/python3 -m pytest ml/tests/test_reward.py ml/tests/test_lyrics_mood_reward.py apps/music/tests/test_lyrics_nlp.py apps/music/tests/test_lyrics_matching.py -v
```

Expected: ALL tests PASS

- [ ] **Step 2: Verify end-to-end with real data**

```bash
/home/ijmadalena/PycharmProjects/moodsic/.venv/bin/python3 manage.py shell -c "
from apps.interactions.services.reward_service import get_reward_service
from apps.music.models import Track, TrackLyrics

svc = get_reward_service()

# Find a track that has both audio features and analyzed lyrics
lyric = TrackLyrics.objects.filter(
    track__isnull=False,
    sentiment_score__isnull=False,
).select_related('track__audio_features').first()

if lyric:
    reward = svc.calculate_interaction_reward(
        user_feedback='completed',
        user=None,
        track=lyric.track,
    )
    print(f'Track: \"{lyric.song_name}\"')
    print(f'Sentiment: {lyric.sentiment_label} ({lyric.sentiment_score:.3f})')
    print(f'Reward: {reward:.4f}')
else:
    print('No tracks with both features and analyzed lyrics. Run analyze_lyrics first.')
"
```

- [ ] **Step 3: Commit final state**

```bash
git add -A
git commit -m "chore: final verification of NLP lyrics + RL integration pipeline"
```

---

## Verification Checklist

After all tasks complete, verify:

- [ ] `python manage.py match_lyrics` links most unmatched lyrics
- [ ] `python manage.py analyze_lyrics` populates sentiment fields
- [ ] `LyricsNLPService.get_mood_score()` returns 0-1 float
- [ ] `RewardCalculator._calculate_lyrics_mood_reward()` affects total reward
- [ ] `RewardService.calculate_interaction_reward()` includes lyrics data
- [ ] All existing tests still pass
- [ ] New model tests for sentiment fields pass
- [ ] Integration test shows reward differences with/without lyrics
