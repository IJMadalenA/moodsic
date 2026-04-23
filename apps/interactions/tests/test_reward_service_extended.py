import pytest

from apps.context.models import NewsContext
from apps.interactions.models import Interaction
from apps.interactions.services.reward_service import RewardService
from apps.music.models import Track, TrackAudioFeatures
from apps.users.models.user import User


@pytest.mark.django_db
class TestRewardServiceExtended:
    @pytest.fixture
    def reward_service(self):
        return RewardService()

    @pytest.fixture
    def user(self):
        return User.objects.create_user(username="reward_user", email="reward@test.com")

    @pytest.fixture
    def track(self):
        return Track.objects.create(
            spotify_id="track_reward_1",
            name="Reward Track",
            duration_ms=200000,
            track_number=1,
            uri="spotify:track:reward_1"
        )

    def test_calculate_interaction_reward_with_news(self, reward_service, user, track):
        # Crear noticias
        news1 = NewsContext.objects.create(
            title="News 1",
            sentiment_score=0.8,
            is_breaking=True,
            source="Test Source",
            url="http://news1.com"
        )
        news2 = NewsContext.objects.create(
            title="News 2",
            sentiment_score=-0.4,
            is_breaking=False,
            source="Test Source",
            url="http://news2.com"
        )

        reward = reward_service.calculate_interaction_reward(
            user_feedback="completed",
            user=user,
            track=track,
            news_ids=[news1.id, news2.id]
        )

        assert isinstance(reward, float)
        assert -2.0 <= reward <= 2.0

    def test_get_weather_context_not_found(self, reward_service):
        context = reward_service._get_weather_context(99999)
        assert context is None

    def test_get_news_context_empty_list(self, reward_service):
        context = reward_service._get_news_context([])
        assert context is None

        context = reward_service._get_news_context([99999])
        assert context is None

    def test_get_track_audio_features_none(self, reward_service, track):
        # track no tiene audio_features
        features = reward_service._get_track_audio_features(track)
        assert features["energy"] == 0.5
        assert features["danceability"] == 0.5

    def test_user_history_with_interactions_missing_audio_features(self, reward_service, user, track):
        # Crear interacción para un track sin audio features
        Interaction.objects.create(
            user=user,
            track=track,
            feedback="completed",
            play_duration=200,
            track_duration=200
        )

        history = reward_service._get_user_history(user)
        assert history["skip_rate"] == 0.0
        assert history["avg_energy"] == 0.5 # Default because no audio features were found

    def test_user_history_with_skips(self, reward_service, user, track):
        # Track con audio features
        af = TrackAudioFeatures.objects.create(
            track=track,
            energy=0.8,
            danceability=0.7,
            valence=0.6,
            key=1,
            loudness=-5.0,
            mode=1,
            speechiness=0.1,
            acousticness=0.1,
            instrumentalness=0.1,
            liveness=0.1,
            tempo=120.0,
            time_signature=4
        )

        # Interacción skip
        Interaction.objects.create(
            user=user,
            track=track,
            feedback="skip",
            play_duration=10,
            track_duration=200
        )

        history = reward_service._get_user_history(user)
        assert history["skip_rate"] == 1.0
        assert history["avg_energy"] == 0.8
        assert history["avg_danceability"] == 0.7
        assert history["avg_valence"] == 0.6
