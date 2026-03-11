from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from ..models import Track, TrackAudioFeatures


class TrackAudioFeaturesInline(TabularInline):
    model = TrackAudioFeatures
    can_delete = False
    extra = 0
    readonly_fields = (
        "danceability",
        "energy",
        "key",
        "loudness",
        "mode",
        "speechiness",
        "acousticness",
        "instrumentalness",
        "liveness",
        "valence",
        "tempo",
        "time_signature",
        "created_at",
    )


@admin.register(Track)
class TrackAdmin(ModelAdmin):
    list_display = ("name", "get_artists", "album", "popularity", "spotify_id")
    search_fields = ("name", "spotify_id", "artists__name", "album__name")
    filter_horizontal = ("artists",)
    inlines = (TrackAudioFeaturesInline,)
    readonly_fields = ("created_at", "updated_at")

    def get_artists(self, obj):
        return ", ".join([a.name for a in obj.artists.all()])

    get_artists.short_description = "Artistas"
