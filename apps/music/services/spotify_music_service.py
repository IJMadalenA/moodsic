import logging

import spotipy
from allauth.socialaccount.models import SocialToken
from django.conf import settings
from django.utils import timezone
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth

logger = logging.getLogger(__name__)

# Constantes para códigos de estado HTTP
HTTP_401_UNAUTHORIZED = 401
HTTP_429_TOO_MANY_REQUESTS = 429


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

    def search_tracks(self, query: str, limit: int = 20, **_kwargs):
        """
        Busca tracks en Spotify.
        Permite filtrar por parámetros de audio si se proporcionan en kwargs.
        Debido a que la API de búsqueda de Spotify no soporta parámetros de audio directamente,
        estos se usarán para filtrar los resultados o como base para recomendaciones si es necesario.
        En esta implementación inicial, realizamos la búsqueda y luego podríamos filtrar
        (aunque el filtrado real por audio suele ser más eficiente vía recommendations).
        """
        if not self.client:
            return None

        results = self.client.search(q=query, limit=limit, type="track")

        # Si hay parámetros de audio en kwargs, podríamos filtrar los resultados aquí.
        # Por ahora, devolvemos los resultados de la búsqueda.
        return results

    def get_recommendations(
        self,
        seed_artists: list | None = None,
        seed_genres: list | None = None,
        seed_tracks: list | None = None,
        limit: int = 20,
        **kwargs,
    ):
        """
        Obtiene recomendaciones basadas en semillas y parámetros de audio.
        """
        if not self.client:
            return None

        try:
            return self.client.recommendations(
                seed_artists=seed_artists,
                seed_genres=seed_genres,
                seed_tracks=seed_tracks,
                limit=limit,
                **kwargs,
            )
        except spotipy.SpotifyException as e:
            logger.error(f"Error en recomendaciones de Spotify: {e}")
            self._handle_spotify_exception(e)
            return None

    def create_playlist(
        self,
        name: str,
        public: bool = True,
        collaborative: bool = False,
        description: str = "",
    ):
        """
        Crea una nueva playlist en la cuenta del usuario.
        """
        if not self.client:
            return None

        try:
            user_id = self.client.current_user()["id"]
            return self.client.user_playlist_create(
                user=user_id,
                name=name,
                public=public,
                collaborative=collaborative,
                description=description,
            )
        except spotipy.SpotifyException as e:
            logger.error(f"Error al crear playlist: {e}")
            self._handle_spotify_exception(e)
            return None

    def add_tracks_to_playlist(self, playlist_id: str, track_uris: list[str]):
        """
        Añade canciones a una playlist existente.
        """
        if not self.client:
            return None

        try:
            return self.client.playlist_add_items(playlist_id, track_uris)
        except spotipy.SpotifyException as e:
            logger.error(f"Error al añadir tracks a la playlist {playlist_id}: {e}")
            self._handle_spotify_exception(e)
            return None

    def replace_playlist_tracks(self, playlist_id: str, track_uris: list[str]):
        """
        Reemplaza todas las canciones de una playlist por una nueva lista.
        Útil para actualizar playlists dinámicas de "Mood".
        """
        if not self.client:
            return None

        try:
            return self.client.playlist_replace_items(playlist_id, track_uris)
        except spotipy.SpotifyException as e:
            logger.error(
                f"Error al reemplazar tracks en la playlist {playlist_id}: {e}"
            )
            self._handle_spotify_exception(e)
            return None

    def _handle_spotify_exception(self, e: spotipy.SpotifyException):
        """
        Manejo centralizado de excepciones de la API de Spotify.
        """
        if e.http_status == HTTP_401_UNAUTHORIZED:
            logger.warning(
                "Token expirado detectado durante la operación. Intentando refrescar..."
            )
            self.token = self._get_valid_token()
            if self.token:
                self.client = spotipy.Spotify(auth=self.token.token)
        elif e.http_status == HTTP_429_TOO_MANY_REQUESTS:
            retry_after = e.headers.get("Retry-After", "desconocido")
            logger.error(
                f"Límite de tasa (Rate Limit) alcanzado. Reintentar después de {retry_after}s."
            )
        else:
            logger.error(f"Error de Spotify API ({e.http_status}): {e.msg}")

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
