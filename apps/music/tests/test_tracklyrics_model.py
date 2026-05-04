import pytest

from apps.music.models import Track, TrackLyrics


@pytest.mark.django_db
class TestTrackLyricsModel:
    def test_create_with_track(self):
        track = Track.objects.create(
            spotify_id="track_789",
            name="Test Song",
            duration_ms=180000,
            track_number=1,
        )
        lyrics = TrackLyrics.objects.create(
            track=track,
            artist_name="Test Artist",
            song_name="Test Song",
            text="La la la la la",
            language="en",
            word_count=5,
            match_score=95,
            match_status="matched",
        )
        assert lyrics.track == track
        assert lyrics.match_status == "matched"
        assert str(lyrics) == "Lyrics for Test Song by Test Artist"
        assert track.lyrics.count() == 1

    def test_create_without_track(self):
        lyrics = TrackLyrics.objects.create(
            artist_name="Unknown Artist",
            song_name="Unknown Song",
            text="Some lyrics here",
            match_status="unmatched",
        )
        assert lyrics.track is None
        assert lyrics.match_score is None
        assert TrackLyrics.objects.filter(match_status="unmatched").count() == 1

    def test_match_status_choices(self):
        lyrics = TrackLyrics.objects.create(
            artist_name="A", song_name="B", text="x", match_status="reviewed"
        )
        assert lyrics.match_status == "reviewed"
        lyrics.match_status = "matched"
        lyrics.save()
        assert lyrics.match_status == "matched"

    def test_track_cascade(self):
        track = Track.objects.create(
            spotify_id="t_cascade", name="X", duration_ms=1000, track_number=1
        )
        TrackLyrics.objects.create(
            track=track,
            artist_name="A",
            song_name="X",
            text="y",
            match_status="matched",
        )
        assert TrackLyrics.objects.count() == 1
        track.delete()
        assert TrackLyrics.objects.count() == 1  # SET_NULL
        assert TrackLyrics.objects.first().track is None
