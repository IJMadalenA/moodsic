from django.core.management import call_command

from apps.music.models import Track, TrackLyrics


class TestMatchLyricsCommand:
    def test_exact_match(self, db):
        track = Track.objects.create(
            spotify_id="s1", name="Hello", duration_ms=200000, track_number=1
        )
        lyric = TrackLyrics.objects.create(
            artist_name="Adele",
            song_name="Hello",
            text="Hello from the other side",
            match_status="unmatched",
        )
        call_command("match_lyrics")
        lyric.refresh_from_db()
        assert lyric.match_status == "matched"
        assert lyric.track == track
        assert lyric.match_score == 100

    def test_fuzzy_match(self, db):
        track = Track.objects.create(
            spotify_id="s2", name="Hello", duration_ms=200000, track_number=1
        )
        lyric = TrackLyrics.objects.create(
            artist_name="Adele",
            song_name="Hello (Live)",
            text="Hello from the other side",
            match_status="unmatched",
        )
        call_command("match_lyrics")
        lyric.refresh_from_db()
        assert lyric.match_status in ("matched", "reviewed")
        assert lyric.track == track

    def test_no_match_remains_unmatched(self, db):
        Track.objects.create(
            spotify_id="s3", name="Unique Song XYZ", duration_ms=200000, track_number=1
        )
        lyric = TrackLyrics.objects.create(
            artist_name="Unknown",
            song_name="Nonexistent Song",
            text="la la la",
            match_status="unmatched",
        )
        call_command("match_lyrics")
        lyric.refresh_from_db()
        assert lyric.match_status == "unmatched"

    def test_already_matched_not_modified(self, db):
        track = Track.objects.create(
            spotify_id="s4", name="Old Song", duration_ms=200000, track_number=1
        )
        lyric = TrackLyrics.objects.create(
            artist_name="A",
            song_name="Old Song",
            text="x",
            match_status="matched",
            match_score=95,
            track=track,
        )
        call_command("match_lyrics")
        lyric.refresh_from_db()
        assert lyric.match_status == "matched"
        assert lyric.match_score == 95
