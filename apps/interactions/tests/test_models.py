"""
Tests para los modelos de Interaction.
"""

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

from apps.interactions.models import Interaction, InteractionSession

User = get_user_model()


@pytest.fixture
def user(db):
    """Fixture con usuario de test."""
    return User.objects.create_user(
        username="testuser",
        email="test@test.com",
        password="testpass123",
    )


@pytest.fixture
def track(db):
    """Fixture con track de test."""
    from apps.music.models import Track, Album

    album = Album.objects.create(name="Test Album")
    return Track.objects.create(
        spotify_id="test_track_123",
        name="Test Track",
        album=album,
        duration_ms=180000,
        explicit=False,
        track_number=1,
        popularity=80,
    )


@pytest.fixture
def weather_context(db):
    """Fixture con contexto de clima."""
    from apps.context.models import WeatherContext

    # Crear WeatherContext con campos necesarios
    return WeatherContext.objects.create(
        main_status="Clear",
        description="Clear sky",
        temperature=25.0,
        feels_like=24.0,
        humidity=60,
        timestamp=timezone.now(),
    )


@pytest.fixture
def session(db, user):
    """Fixture con sesión de interacción."""
    return InteractionSession.objects.create(
        user=user,
    )


@pytest.mark.django_db
class TestInteractionModel:
    """Tests para el modelo Interaction."""

    def test_interaction_creation(self, user, track, weather_context):
        """Test de creación básica de interacción."""
        interaction = Interaction.objects.create(
            user=user,
            track=track,
            feedback="completed",
            weather_id=weather_context.id,
            play_duration=180,
            track_duration=180,
            reward=Decimal("1.0"),
        )

        assert interaction.pk is not None
        assert interaction.user == user
        assert interaction.track == track
        assert interaction.feedback == "completed"

    def test_interaction_completion_percentage(self, user, track, weather_context):
        """Test de cálculo automático de percentage."""
        interaction = Interaction.objects.create(
            user=user,
            track=track,
            feedback="completed",
            weather_id=weather_context.id,
            play_duration=90,  # 50% del track
            track_duration=180,
            reward=Decimal("0.5"),
        )

        # completion_percentage debería ser ~50%
        expected_completion = (90 / 180) * 100
        assert abs(interaction.completion_percentage - expected_completion) < 1.0

    def test_interaction_is_positive_completed(self, user, track, weather_context):
        """Test de feedback positivo (completed)."""
        interaction = Interaction.objects.create(
            user=user,
            track=track,
            feedback="completed",
            weather_id=weather_context.id,
            play_duration=180,
            track_duration=180,
            reward=Decimal("1.0"),
        )

        # completed debería ser positivo
        assert interaction.is_positive is True

    def test_interaction_is_positive_skip(self, user, track, weather_context):
        """Test de feedback negativo (skip)."""
        interaction = Interaction.objects.create(
            user=user,
            track=track,
            feedback="skip",
            weather_id=weather_context.id,
            play_duration=10,
            track_duration=180,
            reward=Decimal("-1.0"),
        )

        assert interaction.is_positive is False

    def test_interaction_is_positive_skip_immediate(self, user, track, weather_context):
        """Test de feedback negativo (skip_immediate)."""
        interaction = Interaction.objects.create(
            user=user,
            track=track,
            feedback="skip_immediate",
            weather_id=weather_context.id,
            play_duration=2,
            track_duration=180,
            reward=Decimal("-1.0"),
        )

        assert interaction.is_positive is False

    def test_interaction_feedback_choices(self, user, track, weather_context):
        """Test de opciones válidas de feedback."""
        valid_feedbacks = ["completed", "skip", "skip_immediate", "replay", "added_to_playlist"]

        for feedback in valid_feedbacks:
            interaction = Interaction.objects.create(
                user=user,
                track=track,
                feedback=feedback,
                weather_id=weather_context.id,
                play_duration=90,
                track_duration=180,
                reward=Decimal("0.0"),
            )
            assert interaction.feedback == feedback

    def test_interaction_default_values(self, user, track, weather_context):
        """Test de valores por defecto."""
        interaction = Interaction.objects.create(
            user=user,
            track=track,
            feedback="completed",
            weather_id=weather_context.id,
            play_duration=180,
            track_duration=180,
            reward=Decimal("1.0"),
        )

        # Debería tener started_at automático
        assert interaction.started_at is not None
        # session_id puede ser nulo o vacío
        assert interaction.session_id == "" or isinstance(interaction.session_id, str)

    def test_interaction_string_representation(self, user, track, weather_context):
        """Test de representación en string."""
        interaction = Interaction.objects.create(
            user=user,
            track=track,
            feedback="completed",
            weather_id=weather_context.id,
            play_duration=180,
            track_duration=180,
            reward=Decimal("1.0"),
        )

        str_repr = str(interaction)
        # Debería contener información legible
        assert len(str_repr) > 0


@pytest.mark.django_db
class TestInteractionSessionModel:
    """Tests para el modelo InteractionSession."""

    def test_session_creation(self, user):
        """Test de creación básica de sesión."""
        session = InteractionSession.objects.create(user=user)

        assert session.pk is not None
        assert session.user == user

    def test_session_default_metrics(self, user):
        """Test de métricas por defecto."""
        session = InteractionSession.objects.create(user=user)

        assert session.total_tracks == 0
        assert session.skip_count == 0
        assert session.completed_count == 0

    def test_session_with_interactions(self, user, track, weather_context):
        """Test de sesión con interacciones."""
        session = InteractionSession.objects.create(user=user)

        # Crear varias interacciones
        for i, feedback in enumerate(["completed", "completed", "skip", "replay"]):
            Interaction.objects.create(
                user=user,
                track=track,
                feedback=feedback,
                weather_id=weather_context.id,
                play_duration=90,
                track_duration=180,
                reward=Decimal(str(1.0 if feedback == "completed" else -1.0)),
                session_id=session.session_id,
            )

        # Debería tener 4 tracks totales (o las métricas que se calculen)
        # Verificar que al menos se guarden

    def test_session_timestamp(self, user):
        """Test de timestamp de sesión."""
        session = InteractionSession.objects.create(user=user)

        assert session.created_at is not None

    def test_session_string_representation(self, user):
        """Test de representación en string."""
        session = InteractionSession.objects.create(user=user)

        str_repr = str(session)
        assert len(str_repr) > 0
        assert user.username in str_repr or "Session" in str_repr


@pytest.mark.django_db
class TestInteractionRelationships:
    """Tests para relaciones entre modelos."""

    def test_interaction_user_relationship(self, user, track, weather_context):
        """Test de relación usuario-interacción."""
        interaction = Interaction.objects.create(
            user=user,
            track=track,
            feedback="completed",
            weather_id=weather_context.id,
            play_duration=180,
            track_duration=180,
        )

        # Debería accederse a través del usuario
        user_interactions = Interaction.objects.filter(user=user)
        assert interaction in user_interactions

    def test_interaction_track_relationship(self, user, track, weather_context):
        """Test de relación track-interacción."""
        interaction = Interaction.objects.create(
            user=user,
            track=track,
            feedback="completed",
            weather_id=weather_context.id,
            play_duration=180,
            track_duration=180,
        )

        # Debería accederse a través del track
        track_interactions = Interaction.objects.filter(track=track)
        assert interaction in track_interactions

    def test_interaction_session_relationship(self, user, track, weather_context, session):
        """Test de relación sesión-interacción."""
        interaction = Interaction.objects.create(
            user=user,
            track=track,
            feedback="completed",
            weather_id=weather_context.id,
            play_duration=180,
            track_duration=180,
            session_id=session.session_id,
        )

        # Debería accederse a través de la sesión
        session_interactions = Interaction.objects.filter(session_id=session.session_id)
        assert interaction in session_interactions

    def test_session_user_relationship(self, user):
        """Test de relación usuario-sesión."""
        session = InteractionSession.objects.create(user=user)

        # Debería accederse a través del usuario
        user_sessions = InteractionSession.objects.filter(user=user)
        assert session in user_sessions
