import pytest
from django.test import Client

from apps.users.models.user import User


@pytest.mark.django_db
class TestUserViewsExtended:
    @pytest.fixture
    def client(self):
        return Client()

    @pytest.fixture
    def user(self):
        return User.objects.create_user(username="view_user", email="view@test.com")

    @pytest.fixture(autouse=True)
    def setup_social_app(self):
        from allauth.socialaccount.models import SocialApp
        from django.contrib.sites.models import Site
        site = Site.objects.get_current()
        app = SocialApp.objects.create(
            provider="spotify",
            name="Spotify",
            client_id="client_id",
            secret="secret"
        )
        app.sites.add(site)
        return app

    def test_profile_view_authenticated(self, client, user):
        client.force_login(user)
        response = client.get("/accounts/profile/")
        assert response.status_code == 200

    def test_spotify_oauth_authenticated(self, client, user):
        client.force_login(user)
        response = client.get("/accounts/spotify/login/")
        assert response.status_code in [302, 200, 401]

    def test_spotify_callback_authenticated(self, client, user):
        client.force_login(user)
        response = client.get("/accounts/spotify/login/callback/")
        assert response.status_code in [302, 200, 401]
