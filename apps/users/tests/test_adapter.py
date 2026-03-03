from unittest.mock import MagicMock

import pytest
from allauth.socialaccount.models import SocialAccount, SocialLogin
from django.contrib.auth import get_user_model

from apps.users.adapter import MoodsicSocialAccountAdapter

User = get_user_model()


@pytest.mark.django_db
def test_adapter_save_user_populates_custom_fields(rf):
    # Setup mock request, sociallogin and user
    request = rf.get("/")
    # Add session to mock request
    from django.contrib.sessions.middleware import SessionMiddleware

    middleware = SessionMiddleware(lambda _: None)
    middleware.process_request(request)
    request.session.save()

    user = User.objects.create_user(
        username="socialuser", email="social@example.com", password="password"
    )

    # Mock SocialAccount and SocialLogin
    social_account = SocialAccount(user=user, provider="spotify", uid="spotify_uid_123")
    social_account.get_avatar_url = MagicMock(
        return_value="https://example.com/social_avatar.jpg"
    )

    social_login = SocialLogin(user=user, account=social_account)

    # Instantiate adapter
    adapter = MoodsicSocialAccountAdapter()

    # Call the method
    saved_user = adapter.save_user(request, social_login)

    assert saved_user == user
    assert saved_user.spotify_id == "spotify_uid_123"
    assert saved_user.avatar_url == "https://example.com/social_avatar.jpg"
    assert saved_user.is_spotify_connected is True


@pytest.mark.django_db
def test_adapter_save_user_updates_existing_fields(rf):
    request = rf.get("/")
    # Add session to mock request
    from django.contrib.sessions.middleware import SessionMiddleware

    middleware = SessionMiddleware(lambda _: None)
    middleware.process_request(request)
    request.session.save()

    user = User.objects.create_user(
        username="socialuser2",
        email="social2@example.com",
        password="password",
        spotify_id="old_id",
    )

    social_account = SocialAccount(user=user, provider="spotify", uid="new_uid")
    social_account.get_avatar_url = MagicMock(
        return_value="https://example.com/new_avatar.jpg"
    )
    social_login = SocialLogin(user=user, account=social_account)

    adapter = MoodsicSocialAccountAdapter()
    adapter.save_user(request, social_login)

    user.refresh_from_db()
    assert user.spotify_id == "new_uid"
    assert user.avatar_url == "https://example.com/new_avatar.jpg"
