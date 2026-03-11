import logging

import spotipy
from allauth.socialaccount.models import SocialToken
from django.conf import settings
from django.utils import timezone
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth

logger = logging.getLogger(__name__)


class SpotifyMusicService:
    """
    Servicio centralizado para interactuar con la API de Spotify.
    Maneja la autenticación, persistencia de tokens y refresco automático.
    """

    def __init__(self, user):
        self.user = user
        self.token = self._get_valid_token()
        self.client = spotipy.Spotify(auth=self.token.token) if self.token else None

    def _get_valid_token(self):
        """
        Obtiene el token de Spotify para el usuario y lo refresca si es necesario.
        """
        try:
            token = SocialToken.objects.get(
                account__user=self.user, account__provider="spotify"
            )
        except SocialToken.DoesNotExist:
            return None

        # Verificar si el token ha expirado (o está a punto de expirar)
        if token.expires_at and token.expires_at <= timezone.now():
            self._refresh_token(token)

        return token

    def _refresh_token(self, token):
        """
        Refresca el token utilizando el refresh_token almacenado.
        """
        sp_oauth = SpotifyOAuth(
            client_id=settings.SPOTIPY_CLIENT_ID,
            client_secret=settings.SPOTIPY_CLIENT_SECRET,
            redirect_uri=settings.SPOTIPY_REDIRECT_URI,
        )

        refresh_token = token.token_secret
        if not refresh_token:
            logger.warning(f"No refresh token found for user {self.user.username}")
            return

        try:
            new_token_info = sp_oauth.refresh_access_token(refresh_token)

            if new_token_info:
                token.token = new_token_info["access_token"]
                if "refresh_token" in new_token_info:
                    token.token_secret = new_token_info["refresh_token"]

                expires_in = new_token_info.get("expires_in", 3600)
                token.expires_at = timezone.now() + timezone.timedelta(
                    seconds=expires_in
                )
                token.save()
                logger.info(
                    f"Token refreshed successfully for user {self.user.username}"
                )
        except Exception as e:
            logger.error(f"Error refreshing token for user {self.user.username}: {e}")

    def get_user_info(self):
        """
        Obtiene información del perfil de Spotify del usuario actual.
        """
        if not self.client:
            return None
        return self.client.current_user()

    @staticmethod
    def verify_api_connection():
        """
        Verifica que las credenciales de la API de Spotify en settings sean válidas
        usando Client Credentials Flow (sin usuario específico).
        """
        try:
            auth_manager = SpotifyClientCredentials(
                client_id=settings.SPOTIPY_CLIENT_ID,
                client_secret=settings.SPOTIPY_CLIENT_SECRET,
            )
            sp = spotipy.Spotify(auth_manager=auth_manager)
            # Intentamos una operación simple
            sp.search(q="test", limit=1)
            return True, "Conexión exitosa con Spotify API."
        except Exception as e:
            return False, f"Error de conexión con Spotify API: {e!s}"
