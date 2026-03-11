from django.db import models
from django.utils.translation import gettext_lazy as _

from .artist import Artist


class Album(models.Model):
    """
    Almacena información básica de un álbum de Spotify.
    """

    spotify_id = models.CharField(
        max_length=255, unique=True, verbose_name=_("Spotify ID")
    )
    name = models.CharField(max_length=255, verbose_name=_("Nombre"))
    album_type = models.CharField(
        max_length=50, blank=True, default="", verbose_name=_("Tipo de álbum")
    )
    total_tracks = models.IntegerField(
        null=True, blank=True, verbose_name=_("Total de canciones")
    )
    release_date = models.CharField(
        max_length=50, blank=True, default="", verbose_name=_("Fecha de lanzamiento")
    )
    images = models.JSONField(default=list, blank=True, verbose_name=_("Imágenes"))
    uri = models.CharField(
        max_length=255, blank=True, default="", verbose_name=_("URI")
    )

    artists = models.ManyToManyField(
        Artist, related_name="albums", verbose_name=_("Artistas")
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Álbum")
        verbose_name_plural = _("Álbumes")
        ordering = ("-release_date", "name")

    def __str__(self):
        return self.name
