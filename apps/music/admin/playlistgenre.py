from django.contrib import admin
from unfold.admin import ModelAdmin

from ..models import PlaylistGenre


@admin.register(PlaylistGenre)
class PlaylistGenreAdmin(ModelAdmin):
    list_display = ("playlist", "genre", "subgenre")
    list_filter = ("genre",)
    search_fields = ("genre", "playlist__name")
    readonly_fields = ("created_at",)
