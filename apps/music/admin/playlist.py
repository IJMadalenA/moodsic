from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from ..models import Playlist, PlaylistTrack


class PlaylistTrackInline(TabularInline):
    model = PlaylistTrack
    extra = 1
    autocomplete_fields = ("track",)


@admin.register(Playlist)
class PlaylistAdmin(ModelAdmin):
    list_display = ("name", "user", "is_public", "spotify_id")
    search_fields = ("name", "user__username", "spotify_id")
    list_filter = ("is_public", "user")
    inlines = (PlaylistTrackInline,)
    readonly_fields = ("created_at", "updated_at")
