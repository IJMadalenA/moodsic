from django.db import models
from django.utils.translation import gettext_lazy as _

from .playlist import Playlist


class PlaylistGenre(models.Model):
    playlist = models.ForeignKey(
        Playlist,
        on_delete=models.CASCADE,
        related_name="genres",
        verbose_name=_("Playlist"),
    )
    genre = models.CharField(max_length=100, verbose_name=_("Género"))
    subgenre = models.CharField(
        max_length=100, blank=True, default="", verbose_name=_("Subgénero")
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Género de playlist")
        verbose_name_plural = _("Géneros de playlists")
        unique_together = [("playlist", "genre")]

    def __str__(self):
        return f"{self.playlist.name} → {self.genre}"
