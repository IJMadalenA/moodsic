from unittest.mock import patch

import pytest
from allauth.socialaccount.models import SocialAccount, SocialLogin, SocialToken
from django.utils import timezone

from apps.users.adapter import MoodsicSocialAccountAdapter
from apps.users.models.user import User


@pytest.mark.django_db
class TestUsersAdapter:
    def test_save_user_with_token(self, rf):
        adapter = MoodsicSocialAccountAdapter()
        request = rf.get("/")
        request.session = {}

        user = User.objects.create(username="test_adapter", email="admin@example.com")

        # Mock get_avatar_url to avoid allauth spotify provider bug with empty images
        account = SocialAccount.objects.create(
            user=user, uid="spotify_uid_123", provider="spotify"
        )
        with patch.object(
            SocialAccount, "get_avatar_url", return_value="http://avatar.com"
        ):
            token = SocialToken.objects.create(
                account=account,
                token="access_123",
                token_secret="refresh_123",
                expires_at=timezone.now(),
            )
            sociallogin = SocialLogin(user=user, account=account, token=token)

            with pytest.MonkeyPatch.context() as m:
                m.setattr("django.conf.settings.ADMINS", ["Admin:admin@example.com"])
                saved_user = adapter.save_user(request, sociallogin)

                assert saved_user.is_spotify_connected is True
                assert saved_user.access_token == "access_123"
                assert saved_user.is_superuser is True

    def test_save_user_no_token(self, rf):
        adapter = MoodsicSocialAccountAdapter()
        request = rf.get("/")
        request.session = {}
        user = User.objects.create(username="test_no_token", email="user@test.com")
        account = SocialAccount.objects.create(
            user=user, uid="spotify_uid_456", provider="spotify"
        )
        with patch.object(SocialAccount, "get_avatar_url", return_value=""):
            sociallogin = SocialLogin(user=user, account=account, token=None)
            saved_user = adapter.save_user(request, sociallogin)
            assert saved_user.is_spotify_connected is True
            assert saved_user.access_token == ""
            assert saved_user.is_superuser is False
