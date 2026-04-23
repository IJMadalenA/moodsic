import pytest
from django.contrib.auth import get_user_model

from apps.music.models import Track

User = get_user_model()

@pytest.mark.django_db
class TestInteractionAPIExtended:
    @pytest.fixture
    def client(self):
        from django.test import Client
        return Client()

    @pytest.fixture
    def user(self):
        return User.objects.create_user(username="api_user", email="api@test.com")

    @pytest.fixture
    def track(self):
        return Track.objects.create(
            spotify_id="track_api_1",
            name="API Track",
            duration_ms=200000,
            track_number=1,
            uri="spotify:track:api_1"
        )

    def test_create_interaction_unauthorized(self, client, track):
        url = "/api/interactions/interactions/"
        payload = {
            "track_id": track.id,
            "feedback": "completed",
            "play_duration": 200,
            "track_duration": 200
        }
        response = client.post(url, payload, content_type="application/json")
        assert response.status_code == 401
        assert response.json()["error"] == "Autenticación requerida"

    def test_create_interaction_track_not_found(self, client, user):
        client.force_login(user)
        url = "/api/interactions/interactions/"
        payload = {
            "track_id": 99999,
            "feedback": "completed",
            "play_duration": 200,
            "track_duration": 200
        }
        response = client.post(url, payload, content_type="application/json")
        assert response.status_code == 404
        assert response.json()["error"] == "Track no encontrado"

    def test_get_session_stats_not_found(self, client, user):
        client.force_login(user)
        url = "/api/interactions/sessions/99999/stats/"
        response = client.get(url)
        assert response.status_code == 404

    def test_dashboard_metrics_forbidden_for_normal_user(self, client, user):
        client.force_login(user)
        url = "/api/interactions/dashboard/metrics/"
        response = client.get(url)
        assert response.status_code == 403
        assert response.json()["error"] == "Permiso denegado"

    def test_dashboard_metrics_staff_access(self, client):
        staff_user = User.objects.create_user(username="staff", email="staff@test.com", is_staff=True)
        client.force_login(staff_user)
        url = "/api/interactions/dashboard/metrics/"
        response = client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert "total_users" in data
        assert "active_sessions" in data
