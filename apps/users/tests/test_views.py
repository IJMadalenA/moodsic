import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


@pytest.mark.django_db
def test_profile_view_requires_login(client):
    url = reverse("users:profile")
    response = client.get(url)
    assert response.status_code == 302
    assert "login" in response.url


@pytest.mark.django_db
def test_profile_view_authenticated(client):
    user = User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="password",
        spotify_id="spotify123",
    )
    client.force_login(user)

    url = reverse("users:profile")
    response = client.get(url)

    assert response.status_code == 200
    assert "test@example.com" in response.content.decode()
    assert "spotify123" in response.content.decode()
    assert "Conectado con Spotify" in response.content.decode()


@pytest.mark.django_db
def test_profile_view_without_spotify(client):
    user = User.objects.create_user(
        username="testuser", email="test@example.com", password="password"
    )
    client.force_login(user)

    url = reverse("users:profile")
    response = client.get(url)

    assert response.status_code == 200
    assert "No conectado con Spotify" in response.content.decode()
