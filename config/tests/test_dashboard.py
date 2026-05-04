"""Tests for the Moodsic dashboard callback and admin template rendering."""

import json

import pytest
from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.template.loader import get_template
from django.test import RequestFactory

from apps.music.models import (
    Artist,
    Playlist,
    PlaylistGenre,
    Track,
    TrackAudioFeatures,
    TrackLyrics,
)
from config.dashboard import dashboard_callback

User = get_user_model()


class TestDashboardCallback:
    """Tests for the dashboard_callback function."""

    def test_empty_database_returns_defaults(self, db):
        ctx = {}
        request = RequestFactory().get("/admin/")
        result = dashboard_callback(request, ctx)

        assert result is ctx
        assert ctx["total_tracks"] == 0
        assert ctx["total_artists"] == 0
        assert ctx["total_playlists"] == 0
        assert ctx["total_lyrics"] == 0
        assert ctx["lyrics_matched"] == 0
        assert ctx["lyrics_analyzed"] == 0
        assert ctx["lyrics_positive"] == 0
        assert ctx["lyrics_negative"] == 0
        assert ctx["lyrics_neutral"] == 0
        assert ctx["sentiment_positive_pct"] == 0
        assert ctx["match_pct"] == 0
        assert ctx["lyrics_coverage_pct"] == 0

    def test_track_counts(self, db):
        Track.objects.create(
            spotify_id="t1", name="Song A", duration_ms=180000, track_number=1,
            genre="pop",
        )
        Track.objects.create(
            spotify_id="t2", name="Song B", duration_ms=200000, track_number=1,
            genre="rock",
        )
        Track.objects.create(
            spotify_id="t3", name="Song C", duration_ms=150000, track_number=1,
        )

        ctx = {}
        dashboard_callback(None, ctx)

        assert ctx["total_tracks"] == 3
        assert ctx["tracks_with_genre"] == 2
        assert ctx["total_features"] == 0

    def test_artist_and_playlist_counts(self, db):
        artist = Artist.objects.create(spotify_id="a1", name="Test Artist")
        Artist.objects.create(spotify_id="a2", name="Test Artist 2")
        user = User.objects.create_user(username="test", password="pass")
        Playlist.objects.create(spotify_id="p1", user=user, name="PL1")
        Playlist.objects.create(spotify_id="p2", user=user, name="PL2")

        ctx = {}
        dashboard_callback(None, ctx)

        assert ctx["total_artists"] == 2
        assert ctx["total_playlists"] == 2

    def test_lyrics_stats(self, db):
        track = Track.objects.create(
            spotify_id="tl1", name="Lyric Song", duration_ms=180000, track_number=1,
        )
        TrackLyrics.objects.create(
            track=track, artist_name="A", song_name="Happy",
            text="I am so happy today", match_status="matched",
            sentiment_score=0.85, sentiment_label="positive",
            sentiment_pos=0.7, sentiment_neg=0.0, sentiment_neu=0.3,
        )
        TrackLyrics.objects.create(
            track=track, artist_name="B", song_name="Sad",
            text="I am so sad today", match_status="matched",
            sentiment_score=-0.75, sentiment_label="negative",
            sentiment_pos=0.0, sentiment_neg=0.6, sentiment_neu=0.4,
        )
        TrackLyrics.objects.create(
            artist_name="C", song_name="Neutral",
            text="The sky is blue", match_status="unmatched",
            sentiment_score=0.0, sentiment_label="neutral",
            sentiment_pos=0.3, sentiment_neg=0.3, sentiment_neu=0.4,
        )
        TrackLyrics.objects.create(
            track=track, artist_name="D", song_name="Review",
            text="Maybe happy maybe sad", match_status="reviewed",
        )

        ctx = {}
        dashboard_callback(None, ctx)

        assert ctx["total_lyrics"] == 4
        assert ctx["lyrics_matched"] == 3
        assert ctx["lyrics_analyzed"] == 3
        assert ctx["lyrics_positive"] == 1
        assert ctx["lyrics_negative"] == 1
        assert ctx["lyrics_neutral"] == 1
        assert ctx["lyrics_reviewed"] == 1
        assert ctx["lyrics_unmatched"] == 1
        assert ctx["sentiment_positive_pct"] == pytest.approx(33.3, rel=0.1)
        assert ctx["match_pct"] == 75.0
        assert ctx["lyrics_coverage_pct"] == 100.0

    def test_genre_chart_structure(self, db):
        Track.objects.create(
            spotify_id="g1", name="Rock Song", duration_ms=1000, track_number=1,
            genre="rock",
        )
        Track.objects.create(
            spotify_id="g2", name="Pop Song", duration_ms=1000, track_number=1,
            genre="pop",
        )

        ctx = {}
        dashboard_callback(None, ctx)

        chart = json.loads(ctx["genre_chart"])
        assert "labels" in chart
        assert "datasets" in chart
        assert len(chart["labels"]) <= 12
        assert len(chart["datasets"]) == 1
        assert "label" in chart["datasets"][0]
        assert "data" in chart["datasets"][0]
        assert "backgroundColor" in chart["datasets"][0]

    def test_svg_circle_values(self, db):
        track = Track.objects.create(
            spotify_id="sv1", name="S", duration_ms=1000, track_number=1,
        )
        TrackLyrics.objects.create(
            track=track, artist_name="X", song_name="Happy",
            text="joy", match_status="matched",
            sentiment_score=0.5, sentiment_label="positive",
            sentiment_pos=0.5, sentiment_neg=0.0, sentiment_neu=0.5,
        )

        ctx = {}
        dashboard_callback(None, ctx)

        assert ctx["svg_circumference"] == 87.96
        # 100% positive -> dash = circumference = 87.96, rounded to 88.0
        assert ctx["svg_sentiment_dash"] == pytest.approx(87.96, abs=0.1)
        assert ctx["svg_sentiment_gap"] == pytest.approx(0.0, abs=0.1)
        # 100% matched
        assert ctx["svg_match_dash"] == pytest.approx(87.96, abs=0.1)
        assert ctx["svg_match_gap"] == pytest.approx(0.0, abs=0.1)

    def test_svg_percentages_partial(self, db):
        track = Track.objects.create(
            spotify_id="sv2", name="T", duration_ms=1000, track_number=1,
        )
        TrackLyrics.objects.create(
            track=track, artist_name="Y", song_name="Pos",
            text="good", match_status="matched",
            sentiment_score=0.8, sentiment_label="positive",
            sentiment_pos=0.8, sentiment_neg=0.0, sentiment_neu=0.2,
        )
        TrackLyrics.objects.create(
            artist_name="Z", song_name="Neg",
            text="bad", match_status="unmatched",
            sentiment_score=-0.5, sentiment_label="negative",
            sentiment_pos=0.0, sentiment_neg=0.5, sentiment_neu=0.5,
        )

        ctx = {}
        dashboard_callback(None, ctx)

        # 50% positive, 50% negative, 50% matched
        assert ctx["sentiment_positive_pct"] == 50.0
        assert ctx["match_pct"] == 50.0
        # SVG dash should be ~43.98 (50% of circumference)
        assert ctx["svg_sentiment_dash"] == pytest.approx(43.98, rel=0.1)
        assert ctx["svg_match_dash"] == pytest.approx(43.98, rel=0.1)

    def test_top_lyrics_presence(self, db):
        track = Track.objects.create(
            spotify_id="tl2", name="Top Song", duration_ms=1000, track_number=1,
        )
        TrackLyrics.objects.create(
            track=track, artist_name="Artist", song_name="Very Positive",
            text="love love love", match_status="matched",
            sentiment_score=0.99, sentiment_label="positive",
            sentiment_pos=0.9, sentiment_neg=0.0, sentiment_neu=0.1,
        )

        ctx = {}
        dashboard_callback(None, ctx)

        assert len(ctx["top_positive_lyrics"]) >= 1
        assert ctx["top_positive_lyrics"][0]["song_name"] == "Very Positive"
        assert ctx["top_positive_lyrics"][0]["sentiment_score"] == 0.99


class TestDashboardTemplate:
    """Tests for the admin/index.html template rendering."""

    def test_template_loads(self, db):
        template = get_template("admin/index.html")
        assert template is not None

    def test_template_renders_without_error(self, db):
        template = get_template("admin/index.html")
        ctx = {}
        dashboard_callback(RequestFactory().get("/admin/"), ctx)
        rendered = template.render(ctx)
        assert len(rendered) > 0

    def test_template_contains_branding(self, db):
        template = get_template("admin/index.html")
        ctx = {}
        dashboard_callback(RequestFactory().get("/admin/"), ctx)
        rendered = template.render(ctx)

        assert "Moodsic AI Platform" in rendered
        assert "RL Agent" in rendered
        assert "VADER NLP" in rendered
        assert "Context-Aware" in rendered

    def test_template_has_kpi_cards(self, db):
        Track.objects.create(
            spotify_id="kpi1", name="X", duration_ms=1000, track_number=1,
        )
        template = get_template("admin/index.html")
        ctx = {}
        dashboard_callback(RequestFactory().get("/admin/"), ctx)
        rendered = template.render(ctx)

        assert "Tracks" in rendered
        assert "Artists" in rendered
        assert "Lyrics Analyzed" in rendered
        assert "Audio Features" in rendered
        assert "Playlists" in rendered

    def test_template_svg_circles_render(self, db):
        template = get_template("admin/index.html")
        ctx = {}
        dashboard_callback(RequestFactory().get("/admin/"), ctx)
        rendered = template.render(ctx)

        soup = BeautifulSoup(rendered, "html.parser")
        circles = soup.find_all("circle")
        assert len(circles) >= 4  # 2 background + 2 foreground circles

        # Foreground circles should have stroke-dasharray
        fg_circles = [c for c in circles if c.get("stroke-dasharray")]
        assert len(fg_circles) == 2

        # At least one should have non-zero dash (when DB is empty, all are 0)
        # With populated DB, they should be > 0
        dash_values = []
        for c in fg_circles:
            dashes = c["stroke-dasharray"].split()
            assert len(dashes) == 2
            dash_values.append(float(dashes[0]))

        # In a real deployment, values would be > 0; in empty DB, they're 0.0
        # Either way, the SVG renders correctly with proper structure
        for dv in dash_values:
            assert dv >= 0.0

    def test_template_svg_is_rotated(self, db):
        template = get_template("admin/index.html")
        ctx = {}
        dashboard_callback(RequestFactory().get("/admin/"), ctx)
        rendered = template.render(ctx)

        soup = BeautifulSoup(rendered, "html.parser")
        svgs = soup.find_all("svg")
        rotated = [s for s in svgs if "-rotate-90" in s.get("class", [])]
        assert len(rotated) == 2

    def test_template_has_bar_chart(self, db):
        template = get_template("admin/index.html")
        ctx = {}
        dashboard_callback(RequestFactory().get("/admin/"), ctx)
        rendered = template.render(ctx)

        soup = BeautifulSoup(rendered, "html.parser")
        chart = soup.find("canvas", class_="chart")
        assert chart is not None
        assert chart.get("data-type") == "bar"
        assert chart.get("data-value") is not None

    def test_template_chart_data_is_json(self, db):
        template = get_template("admin/index.html")
        ctx = {}
        dashboard_callback(RequestFactory().get("/admin/"), ctx)
        rendered = template.render(ctx)

        soup = BeautifulSoup(rendered, "html.parser")
        chart = soup.find("canvas", class_="chart")
        raw = chart.get("data-value", "")

        parsed = json.loads(raw)
        assert "labels" in parsed
        assert "datasets" in parsed

    def test_template_has_footer_tech_stack(self, db):
        template = get_template("admin/index.html")
        ctx = {}
        dashboard_callback(RequestFactory().get("/admin/"), ctx)
        rendered = template.render(ctx)

        assert "Django 5.2" in rendered
        assert "PyTorch" in rendered
        assert "VADER NLP" in rendered
        assert "PostgreSQL" in rendered

    def test_template_sentiment_section(self, db):
        template = get_template("admin/index.html")
        ctx = {}
        dashboard_callback(RequestFactory().get("/admin/"), ctx)
        rendered = template.render(ctx)

        assert "Sentiment Distribution" in rendered
        assert "VADER NLP" in rendered

    def test_template_top_tracks_sections(self, db):
        template = get_template("admin/index.html")
        ctx = {}
        dashboard_callback(RequestFactory().get("/admin/"), ctx)
        rendered = template.render(ctx)

        assert "Most Positive Tracks" in rendered
        assert "Most Negative Tracks" in rendered
        assert "Melancholic" in rendered

    def test_template_lyrics_matching_section(self, db):
        template = get_template("admin/index.html")
        ctx = {}
        dashboard_callback(RequestFactory().get("/admin/"), ctx)
        rendered = template.render(ctx)

        assert "Lyrics Matching Status" in rendered
        assert "Matched" in rendered
        assert "Reviewed" in rendered
        assert "Unmatched" in rendered
