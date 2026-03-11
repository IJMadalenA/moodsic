from django.db import models
from django.utils.translation import gettext_lazy as _

from .album import Album
from .artist import Artist


class Track(models.Model):
    """
    Almacena información básica de una canción de Spotify.
    """

    spotify_id = models.CharField(
        max_length=255, unique=True, verbose_name=_("Spotify ID")
    )
    name = models.CharField(max_length=255, verbose_name=_("Nombre"))
    album = models.ForeignKey(
        Album,
        on_delete=models.CASCADE,
        related_name="tracks",
        verbose_name=_("Álbum"),
        null=True,
        blank=True,
    )
    artists = models.ManyToManyField(
        Artist, related_name="tracks", verbose_name=_("Artistas")
    )
    duration_ms = models.IntegerField(verbose_name=_("Duración (ms)"))
    explicit = models.BooleanField(default=False, verbose_name=_("Explícito"))
    popularity = models.IntegerField(
        null=True, blank=True, verbose_name=_("Popularidad")
    )
    preview_url = models.URLField(
        max_length=500, blank=True, verbose_name=_("URL de previsualización")
    )
    track_number = models.IntegerField(verbose_name=_("Número de pista"))
    uri = models.CharField(
        max_length=255, blank=True, default="", verbose_name=_("URI")
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Canción")
        verbose_name_plural = _("Canciones")
        ordering = ("name",)

    def __str__(self):
        return f"{self.name} - {', '.join([a.name for a in self.artists.all()])}"


class TrackAudioFeatures(models.Model):
    """
    Almacena las características de audio de una canción proporcionadas por Spotify.
    Crucial para el agente de Reinforcement Learning.
    """

    track = models.OneToOneField(
        Track,
        on_delete=models.CASCADE,
        related_name="audio_features",
        verbose_name=_("Canción"),
    )
    danceability = models.FloatField(verbose_name=_("Danceability"))
    energy = models.FloatField(verbose_name=_("Energy"))
    key = models.IntegerField(verbose_name=_("Key"))
    loudness = models.FloatField(verbose_name=_("Loudness"))
    mode = models.IntegerField(verbose_name=_("Mode"))
    speechiness = models.FloatField(verbose_name=_("Speechiness"))
    acousticness = models.FloatField(verbose_name=_("Acousticness"))
    instrumentalness = models.FloatField(verbose_name=_("Instrumentalness"))
    liveness = models.FloatField(verbose_name=_("Liveness"))
    valence = models.FloatField(verbose_name=_("Valence"))
    tempo = models.FloatField(verbose_name=_("Tempo"))
    time_signature = models.IntegerField(verbose_name=_("Time Signature"))

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Características de audio")
        verbose_name_plural = _("Características de audio")

    def __str__(self):
        return f"Features for {self.track.name}"
