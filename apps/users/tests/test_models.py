import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

User = get_user_model()


@pytest.mark.django_db
def test_custom_user_creation():
    user = User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="password",
        spotify_id="spotify123",
        avatar_url="https://example.com/avatar.jpg",
    )

    assert User.objects.count() == 1
    assert user.username == "testuser"
    assert user.email == "test@example.com"
    assert user.spotify_id == "spotify123"
    assert user.avatar_url == "https://example.com/avatar.jpg"


@pytest.mark.django_db
def test_user_str_representation():
    user = User.objects.create_user(
        username="testuser", email="test@example.com", password="password"
    )
    assert str(user) == "test@example.com"

    user2 = User.objects.create_user(username="testuser2", password="password")
    assert str(user2) == "testuser2"


@pytest.mark.django_db
def test_spotify_id_unique():
    User.objects.create_user(username="user1", spotify_id="spotify123")
    with pytest.raises(IntegrityError):
        User.objects.create_user(username="user2", spotify_id="spotify123")
