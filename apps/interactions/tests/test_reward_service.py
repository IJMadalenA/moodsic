import pytest
from django.contrib.auth import get_user_model

from apps.interactions.services.reward_service import RewardService
from apps.music.models import Album, Artist, Track

User = get_user_model()


@pytest.mark.django_db
class TestRewardService:
    def _build_track(self, suffix: str = "1") -> Track:
        album = Album.objects.create(
            spotify_id=f"album_{suffix}", name=f"Album {suffix}"
        )
        artist = Artist.objects.create(
            spotify_id=f"artist_{suffix}",
            name=f"Artist {suffix}",
            genres=["pop"],
        )
        track = Track.objects.create(
            spotify_id=f"track_{suffix}",
            name=f"Track {suffix}",
            album=album,
            duration_ms=180000,
            explicit=False,
            track_number=1,
            popularity=70,
            uri=f"spotify:track:track_{suffix}",
        )
        track.artists.add(artist)
        return track

    def test_calculate_interaction_reward_returns_float(self):
        user = User.objects.create_user(
            "reward_user", "reward@example.com", "pass12345"
        )
        track = self._build_track("float")
        service = RewardService()

        reward = service.calculate_interaction_reward(
            user_feedback="completed",
            user=user,
            track=track,
        )

        assert isinstance(reward, float)
        assert -2.0 <= reward <= 2.0

    def test_skip_feedback_penalizes_more_than_completed(self):
        user = User.objects.create_user(
            "reward_user2", "reward2@example.com", "pass12345"
        )
        track = self._build_track("compare")
        service = RewardService()

        reward_completed = service.calculate_interaction_reward(
            user_feedback="completed",
            user=user,
            track=track,
        )
        reward_skip = service.calculate_interaction_reward(
            user_feedback="skip",
            user=user,
            track=track,
        )

        assert reward_skip < reward_completed
