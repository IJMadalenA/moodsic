"""
Dashboard callback for Moodsic admin landing page.
Inject rich AI/ML statistics into the Unfold dashboard template.
"""

from __future__ import annotations

import json

from django.db.models import Count

from apps.music.models import Artist, Playlist, Track, TrackAudioFeatures, TrackLyrics


def dashboard_callback(request, context):

    # ── KPI metrics ──────────────────────────────────────────────
    total_tracks = Track.objects.count()
    total_artists = Artist.objects.count()
    total_playlists = Playlist.objects.count()

    total_lyrics = TrackLyrics.objects.count()
    lyrics_matched = TrackLyrics.objects.filter(track__isnull=False).count()
    lyrics_analyzed = TrackLyrics.objects.filter(sentiment_score__isnull=False).count()
    lyrics_positive = TrackLyrics.objects.filter(sentiment_label="positive").count()
    lyrics_negative = TrackLyrics.objects.filter(sentiment_label="negative").count()

    total_features = TrackAudioFeatures.objects.count()
    tracks_with_genre = Track.objects.exclude(genre="").count()

    # ── Sentiment distribution chart ─────────────────────────────
    sentiment_chart = json.dumps({
        "type": "doughnut",
        "data": {
            "labels": ["Positive", "Negative", "Neutral"],
            "datasets": [{
                "label": "Lyrics Sentiment",
                "data": [
                    lyrics_positive,
                    lyrics_negative,
                    lyrics_analyzed - lyrics_positive - lyrics_negative,
                ],
                "backgroundColor": [
                    "rgb(16, 185, 129)",   # green
                    "rgb(239, 68, 68)",    # red
                    "rgb(148, 163, 184)",  # gray
                ],
                "borderWidth": 0,
            }],
        },
    })

    # ── Top genres chart ─────────────────────────────────────────
    top_genres = (
        Track.objects.exclude(genre="")
        .values("genre")
        .annotate(count=Count("id"))
        .order_by("-count")[:12]
    )
    genre_chart = json.dumps({
        "labels": [g["genre"] for g in top_genres],
        "datasets": [{
            "label": "Tracks",
            "data": [g["count"] for g in top_genres],
            "backgroundColor": [
                "#3b82f6", "#8b5cf6", "#22c55e", "#f59e0b", "#ef4444",
                "#06b6d4", "#ec4899", "#84cc16", "#f97316", "#6366f1",
                "#14b8a6", "#a855f7",
            ],
        }],
    })

    # ── Matching breakdown ───────────────────────────────────────
    matched_count = TrackLyrics.objects.filter(match_status="matched").count()
    reviewed_count = TrackLyrics.objects.filter(match_status="reviewed").count()
    unmatched_count = total_lyrics - matched_count - reviewed_count

    lyrics_breakdown_chart = json.dumps({
        "type": "pie",
        "data": {
            "labels": ["Matched", "Reviewed", "Unmatched"],
            "datasets": [{
                "data": [
                    matched_count,
                    reviewed_count,
                    unmatched_count,
                ],
                "backgroundColor": [
                    "rgb(59, 130, 246)",
                    "rgb(234, 179, 8)",
                    "rgb(148, 163, 184)",
                ],
                "borderWidth": 0,
            }],
        },
    })

    # ── Recent top sentiment tracks (positive) ───────────────────
    top_positive_lyrics = list(
        TrackLyrics.objects.filter(
            sentiment_label="positive", track__isnull=False
        )
        .select_related("track")
        .order_by("-sentiment_score")[:5]
        .values("song_name", "artist_name", "sentiment_score")
    )

    # ── Top negative tracks for contrast ─────────────────────────
    top_negative_lyrics = list(
        TrackLyrics.objects.filter(
            sentiment_label="negative", track__isnull=False
        )
        .select_related("track")
        .order_by("sentiment_score")[:5]
        .values("song_name", "artist_name", "sentiment_score")
    )

    # ── Populate context ─────────────────────────────────────────
    lyrics_coverage_pct = round((lyrics_matched / total_tracks * 100), 1) if total_tracks else 0
    lyrics_coverage_pct = min(lyrics_coverage_pct, 100.0)  # cap at 100%
    lyrics_neutral = lyrics_analyzed - lyrics_positive - lyrics_negative
    sentiment_positive_pct = round((lyrics_positive / lyrics_analyzed * 100), 1) if lyrics_analyzed else 0
    match_pct = round((lyrics_matched / total_lyrics * 100), 1) if total_lyrics else 0

    # SVG radial circle dasharray: circumference = 2 * pi * r = 87.96
    svg_circumference = 87.96
    svg_sentiment_dash = round(sentiment_positive_pct / 100 * svg_circumference, 1)
    svg_match_dash = round(match_pct / 100 * svg_circumference, 1)

    context.update({
        # KPIs
        "total_tracks": total_tracks,
        "total_artists": total_artists,
        "total_playlists": total_playlists,
        "total_lyrics": total_lyrics,
        "lyrics_matched": lyrics_matched,
        "lyrics_analyzed": lyrics_analyzed,
        "lyrics_positive": lyrics_positive,
        "lyrics_negative": lyrics_negative,
        "lyrics_neutral": lyrics_neutral,
        "lyrics_reviewed": reviewed_count,
        "lyrics_unmatched": unmatched_count,
        "total_features": total_features,
        "tracks_with_genre": tracks_with_genre,
        "match_pct": match_pct,
        "sentiment_positive_pct": sentiment_positive_pct,
        "lyrics_coverage_pct": lyrics_coverage_pct,
        "svg_circumference": svg_circumference,
        "svg_sentiment_dash": svg_sentiment_dash,
        "svg_sentiment_gap": round(svg_circumference - svg_sentiment_dash, 1),
        "svg_match_dash": svg_match_dash,
        "svg_match_gap": round(svg_circumference - svg_match_dash, 1),

        # Charts
        "sentiment_chart": sentiment_chart,
        "genre_chart": genre_chart,
        "lyrics_breakdown_chart": lyrics_breakdown_chart,

        # Top tracks
        "top_positive_lyrics": top_positive_lyrics,
        "top_negative_lyrics": top_negative_lyrics,
    })

    return context
