from django.contrib import admin
from unfold.admin import ModelAdmin

from ..models import Album


@admin.register(Album)
class AlbumAdmin(ModelAdmin):
    list_display = ("name", "spotify_id", "album_type", "release_date")
    search_fields = ("name", "spotify_id")
    filter_horizontal = ("artists",)
    readonly_fields = ("created_at", "updated_at")
