from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from .track import Track


class Playlist(models.Model):
    """
    Almacena información de una lista de reproducción de Spotify.
    """

    spotify_id = models.CharField(
        max_length=255, unique=True, verbose_name=_("Spotify ID")
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="playlists",
        verbose_name=_("Usuario"),
    )
    name = models.CharField(max_length=255, verbose_name=_("Nombre"))
    description = models.TextField(blank=True, verbose_name=_("Descripción"))
    is_public = models.BooleanField(default=True, verbose_name=_("Es pública"))
    snapshot_id = models.CharField(
        max_length=255, blank=True, default="", verbose_name=_("Snapshot ID")
    )
    images = models.JSONField(default=list, blank=True, verbose_name=_("Imágenes"))
    uri = models.CharField(
        max_length=255, blank=True, default="", verbose_name=_("URI")
    )

    tracks = models.ManyToManyField(
        Track,
        through="PlaylistTrack",
        related_name="playlists",
        verbose_name=_("Canciones"),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Lista de reproducción")
        verbose_name_plural = _("Listas de reproducción")
        ordering = ("-updated_at", "name")

    def __str__(self):
        return f"{self.name} ({self.user.username})"


class PlaylistTrack(models.Model):
    """
    Modelo intermedio para gestionar las canciones en una playlist y su orden/fecha.
    """

    playlist = models.ForeignKey(
        Playlist, on_delete=models.CASCADE, verbose_name=_("Lista de reproducción")
    )
    track = models.ForeignKey(
        Track, on_delete=models.CASCADE, verbose_name=_("Canción")
    )
    added_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Añadida en"))
    order = models.IntegerField(default=0, verbose_name=_("Orden"))

    class Meta:
        verbose_name = _("Canción de la lista")
        verbose_name_plural = _("Canciones de la lista")
        ordering = ("playlist", "order")

    def __str__(self):
        return f"{self.playlist.name} - {self.track.name}"
