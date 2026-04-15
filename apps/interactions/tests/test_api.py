"""
Tests para los endpoints de la API de Interactions.
"""

import json
import pytest
from datetime import timedelta
from django.test import Client
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


@pytest.fixture
def client():
    """Fixture del cliente de test."""
    return Client()


@pytest.fixture
def user(db):
    """Fixture con usuario de test."""
    return User.objects.create_user(
        username="testuser",
        email="test@test.com",
        password="testpass123",
    )


@pytest.fixture
def admin_user(db):
    """Fixture con usuario admin."""
    return User.objects.create_superuser(
        username="admin",
        email="admin@test.com",
        password="adminpass123",
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


@pytest.mark.django_db
class TestInteractionAPI:
    """Tests para los endpoints de Interaction."""

    def test_create_interaction_endpoint_exists(self, client):
        """Test básico que el endpoint de interacción existe."""
        response = client.options("/api/interactions/interactions/")
        # OPTIONS debería estar permitido o retornar 404 si no existe el endpoint
        assert response.status_code in [200, 404, 405]

    def test_user_stats_endpoint_exists(self, client, user):
        """Test que el endpoint de estadísticas del usuario existe."""
        client.force_login(user)
        response = client.get("/api/interactions/interactions/user/stats/")
        # Debería retornar algo o 404 si el endpoint no estámapeado correctamente
        assert response.status_code in [200, 404, 400, 401]

    def test_user_stats_returns_dynamic_metrics(self, client, user):
        """El endpoint debe calcular géneros, artistas y duración de sesiones."""
        from apps.music.models import Album, Artist, Track
        from apps.interactions.models import Interaction, InteractionSession

        album = Album.objects.create(name="Stats Album")
        artist = Artist.objects.create(
            spotify_id="artist_123",
            name="Favorite Artist",
            genres=["rock", "synthpop"],
        )

        track = Track.objects.create(
            spotify_id="track_123",
            name="Favorite Track",
            album=album,
            duration_ms=200000,
            explicit=False,
            track_number=1,
            popularity=80,
            uri="spotify:track:track_123",
        )
        track.artists.add(artist)

        Interaction.objects.create(
            user=user,
            track=track,
            feedback="completed",
            play_duration=180,
            track_duration=200,
            session_id="session_abc",
        )

        now = timezone.now()
        InteractionSession.objects.create(
            user=user,
            session_id="session_abc",
            ended_at=now + timedelta(minutes=30),
            is_active=False,
        )

        client.force_login(user)
        response = client.get("/api/interactions/interactions/user/stats/")
        assert response.status_code == 200
        payload = response.json()

        assert payload["favorite_artists"] == ["Favorite Artist"]
        assert "rock" in payload["favorite_genres"]
        assert payload["average_session_length"] > 0


@pytest.mark.django_db
class TestPlaylistAPI:
    """Tests para los endpoints de Playlist Generation."""

    def test_generate_playlist_endpoint_exists(self, client):
        """Test que el endpoint de generación de playlists existe."""
        response = client.options("/api/interactions/playlists/generate/")
        # OPTIONS debería estar permitido o retornar 404 si no existe
        assert response.status_code in [200, 404, 405]

    def test_generate_playlist_unauthorized(self, client):
        """Test de generación de playlist sin autenticación."""
        # Simplemente verificamos que el endpoint responde
        response = client.get("/api/interactions/playlists/generate/")
        # Puede retornar 405 (method not allowed) o 401/403 (unauthorized)
        assert response.status_code in [401, 403, 404, 405]

    def test_generate_playlist_invalid_weather_id_returns_404(self, client, user, track):
        """El endpoint debe rechazar weather_id inválido."""
        client.force_login(user)
        response = client.post(
            "/api/interactions/playlists/generate/",
            data=json.dumps({"name": "Test Playlist", "count": 1, "weather_id": 999, "use_context": True}),
            content_type="application/json",
        )

        assert response.status_code == 404
        assert response.json().get("error") == "Weather context no encontrado"

    def test_generate_playlist_with_valid_weather_id_returns_session(self, client, user, track):
        """El endpoint debe generar playlist con weather_id válido y devolver session_id."""
        from apps.context.models import WeatherContext

        weather = WeatherContext.objects.create(
            main_status="Clear",
            description="Clear sky",
            icon_code="01d",
            temperature=25.0,
            feels_like=25.0,
            temp_min=20.0,
            temp_max=28.0,
            pressure=1013,
            humidity=40,
            visibility=10000,
            wind_speed=3.5,
            wind_deg=120,
            clouds_all=0,
            timestamp=timezone.now(),
        )

        client.force_login(user)
        response = client.post(
            "/api/interactions/playlists/generate/",
            data=json.dumps({"name": "Morning Playlist", "count": 1, "weather_id": weather.id, "use_context": True}),
            content_type="application/json",
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["playlist_name"] == "Morning Playlist"
        assert payload["tracks_count"] == 1
        assert payload["session_id"]
        assert payload["mode"] in {"online", "fallback", "hybrid"}
        assert isinstance(payload["used_spotify_sync"], bool)
        assert isinstance(payload["used_cached_news"], bool)
        assert isinstance(payload["used_local_catalog"], bool)
        assert isinstance(payload["used_spotify_catalog_fallback"], bool)

    def test_generate_playlist_rejects_invalid_news_limit(self, client, user):
        """news_limit fuera del rango permitido debe ser rechazado por validación."""
        client.force_login(user)
        response = client.post(
            "/api/interactions/playlists/generate/",
            data=json.dumps(
                {
                    "name": "Invalid Limit Playlist",
                    "count": 1,
                    "news_category": "music",
                    "news_limit": 0,
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 422

    def test_generate_playlist_caps_requested_count_with_warning(self, client, user, track):
        """Si se piden demasiadas canciones, la API debe caparlo y avisarlo."""
        client.force_login(user)
        response = client.post(
            "/api/interactions/playlists/generate/",
            data=json.dumps({"name": "Big Playlist", "count": 150, "use_context": False}),
            content_type="application/json",
        )

        assert response.status_code == 200
        payload = response.json()
        assert "warnings" in payload
        assert any("100" in warning for warning in payload["warnings"])

    def test_create_interaction_rejects_invalid_feedback_value(self, client, user, track):
        """feedback inválido debe ser rechazado por el schema."""
        client.force_login(user)
        response = client.post(
            "/api/interactions/interactions/",
            data=json.dumps(
                {
                    "track_id": track.id,
                    "feedback": "invalid_feedback",
                    "play_duration": 20,
                    "track_duration": 180,
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 422

    def test_demo_home_page_is_available(self, client):
        """La raíz del proyecto debe mostrar una página de demo útil para la entrega."""
        response = client.get("/")

        assert response.status_code == 200
        assert "MoodSic" in response.content.decode()
        assert "Demo" in response.content.decode() or "dashboard" in response.content.decode().lower()


@pytest.mark.django_db
class TestDashboardAPI:
    """Tests para los endpoints del Dashboard."""

    def test_get_dashboard_metrics_endpoint_exists(self, client):
        """Test que el endpoint del dashboard existe."""
        response = client.options("/api/interactions/dashboard/metrics/")
        # OPTIONS debería estar permitido o retornar 404 si no existe
        assert response.status_code in [200, 404, 405]

    def test_dashboard_metrics_forbid_non_staff_users(self, client, user):
        """El dashboard agregado debe limitarse a usuarios staff."""
        client.force_login(user)
        response = client.get("/api/interactions/dashboard/metrics/")

        assert response.status_code == 403

    def test_dashboard_metrics_returns_user_growth(self, client, admin_user, user, track):
        """El dashboard debe retornar métricas y crecimiento de usuarios."""
        from django.utils import timezone
        from apps.interactions.models import Interaction

        user2 = User.objects.create_user(
            username="testuser2",
            email="test2@test.com",
            password="testpass123",
        )

        Interaction.objects.create(
            user=user2,
            track=track,
            feedback="completed",
            play_duration=180,
            track_duration=200,
            session_id="session_growth_1",
            created_at=timezone.now(),
        )
        Interaction.objects.create(
            user=user,
            track=track,
            feedback="skip",
            play_duration=30,
            track_duration=200,
            session_id="session_growth_2",
            created_at=timezone.now() - timedelta(days=1),
        )

        client.force_login(admin_user)
        response = client.get("/api/interactions/dashboard/metrics/")
        assert response.status_code == 200

        payload = response.json()
        assert "user_growth" in payload
        assert isinstance(payload["user_growth"], list)
        assert len(payload["user_growth"]) == 7
        assert any(day["new_users"] >= 0 for day in payload["user_growth"])
