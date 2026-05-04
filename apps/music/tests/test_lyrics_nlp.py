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
