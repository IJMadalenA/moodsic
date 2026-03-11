from django.contrib import admin
from unfold.admin import ModelAdmin

from ..models import Artist


@admin.register(Artist)
class ArtistAdmin(ModelAdmin):
    list_display = ("name", "spotify_id", "popularity")
    search_fields = ("name", "spotify_id")
    readonly_fields = ("created_at", "updated_at")
