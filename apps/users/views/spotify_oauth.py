from allauth.socialaccount.adapter import get_adapter
from allauth.socialaccount.providers.spotify.views import SpotifyOAuth2Adapter
from allauth.socialaccount.providers.oauth2.views import OAuth2CallbackView, OAuth2LoginView
from allauth.socialaccount.providers.base import ProviderException


class MoodsicSpotifyOAuth2Adapter(SpotifyOAuth2Adapter):
    """Spotify adapter compatible with profile fetch via Authorization header."""

    def complete_login(self, request, app, token, **kwargs):
        with get_adapter().get_requests_session() as sess:
            resp = sess.get(
                self.profile_url,
                headers={"Authorization": f"Bearer {token.token}"},
                timeout=15,
            )
            if resp.status_code >= 400:
                raise ProviderException(
                    f"Spotify profile request failed ({resp.status_code}): {resp.text[:300]}"
                )
            try:
                extra_data = resp.json()
            except ValueError as exc:
                raise ProviderException(
                    f"Spotify profile response is not valid JSON: {resp.text[:300]}"
                ) from exc

        return self.get_provider().sociallogin_from_response(request, extra_data)


spotify_oauth_login = OAuth2LoginView.adapter_view(MoodsicSpotifyOAuth2Adapter)
spotify_oauth_callback = OAuth2CallbackView.adapter_view(MoodsicSpotifyOAuth2Adapter)
