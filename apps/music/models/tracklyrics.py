from django.db import models
from django.utils.translation import gettext_lazy as _

from .track import Track


class TrackLyrics(models.Model):
    track = models.ForeignKey(
        Track,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lyrics",
        verbose_name=_("Canción"),
    )
    artist_name = models.CharField(max_length=255, verbose_name=_("Artista (CSV)"))
    song_name = models.CharField(max_length=255, verbose_name=_("Canción (CSV)"))
    text = models.TextField(verbose_name=_("Letra"))
    language = models.CharField(
        max_length=10, blank=True, default="", verbose_name=_("Idioma")
    )
    word_count = models.IntegerField(
        null=True, blank=True, verbose_name=_("Número de palabras")
    )
    match_score = models.IntegerField(
        null=True, blank=True, verbose_name=_("Score de coincidencia")
    )
    match_status = models.CharField(
        max_length=20,
        default="unmatched",
        verbose_name=_("Estado de coincidencia"),
    )
    source = models.CharField(
        max_length=50, default="mill-song-data", verbose_name=_("Fuente")
    )
    sentiment_score = models.FloatField(
        null=True, blank=True, verbose_name=_("Sentiment compound")
    )
    sentiment_label = models.CharField(
        max_length=20, blank=True, default="", verbose_name=_("Sentiment label")
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

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Letra de canción")
        verbose_name_plural = _("Letras de canciones")
        indexes = [
            models.Index(fields=["match_status"]),
            models.Index(fields=["track"]),
        ]

    def __str__(self):
        return f"Lyrics for {self.song_name} by {self.artist_name}"
