from django.db import models
from django.utils.translation import gettext_lazy as _


class Artist(models.Model):
    """
    Almacena información básica de un artista de Spotify.
    """

    spotify_id = models.CharField(
        max_length=255, unique=True, verbose_name=_("Spotify ID")
    )
    name = models.CharField(max_length=255, verbose_name=_("Nombre"))
    popularity = models.IntegerField(
        null=True, blank=True, verbose_name=_("Popularidad")
    )
    genres = models.JSONField(default=list, blank=True, verbose_name=_("Géneros"))
    images = models.JSONField(default=list, blank=True, verbose_name=_("Imágenes"))
    uri = models.CharField(
        max_length=255, blank=True, default="", verbose_name=_("URI")
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Artista")
        verbose_name_plural = _("Artistas")
        ordering = ("name",)

    def __str__(self):
        return self.name
