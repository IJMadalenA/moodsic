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
