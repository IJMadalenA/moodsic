from django.contrib import admin
from unfold.admin import ModelAdmin

from ..models import TrackLyrics


@admin.register(TrackLyrics)
class TrackLyricsAdmin(ModelAdmin):
    list_display = (
        "song_name",
        "artist_name",
        "match_status",
        "match_score",
        "sentiment_label",
        "sentiment_score",
        "language",
        "word_count",
    )
    list_filter = ("match_status", "sentiment_label", "language")
    search_fields = ("song_name", "artist_name", "text")
    readonly_fields = ("created_at",)
