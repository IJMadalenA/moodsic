import logging
import spotipy
from allauth.socialaccount.models import SocialToken
from django.conf import settings
from django.utils import timezone
from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials

logger = logging.getLogger(__name__)

# Constantes para códigos de estado HTTP
HTTP_401_UNAUTHORIZED = 401
HTTP_429_TOO_MANY_REQUESTS = 429

class SpotifyMusicService:
    """
    Servicio centralizado para interactuar con la API de Spotify.
    Maneja la autenticación mediante SocialToken de allauth y creación de playlists.
    """

    def __init__(self, user):
        self.user = user
        self.client = None
        self.spotify_user_id = None
        
        # Llama al método de abajo para buscar en SocialToken
        self.token = self._get_valid_token()
        
        if self.token:
            self.client = spotipy.Spotify(auth=self.token.token, requests_timeout=10)
            try:
                me = self.client.current_user()
                self.spotify_user_id = me['id']
                print(f"✅ Conectado a Spotify: {self.spotify_user_id}")
            except Exception as e:
                print(f"⚠️ Error al validar cliente Spotify: {e}")
                self.client = None

    def _get_valid_token(self):
        """Busca el token en la tabla SocialToken de allauth."""
        try:
            from allauth.socialaccount.models import SocialToken
            return SocialToken.objects.filter(
                account__user=self.user, 
                account__provider="spotify"
            ).first()
        except Exception as e:
            logger.error(f"Error al recuperar token de la DB: {e}")
            return None

    def _refresh_token(self, token):
        """Refresca el token utilizando el refresh_token almacenado en token_secret."""
        sp_oauth = SpotifyOAuth(
            client_id=settings.SPOTIPY_CLIENT_ID,
            client_secret=settings.SPOTIPY_CLIENT_SECRET,
            redirect_uri=settings.SPOTIPY_REDIRECT_URI,
        )

        refresh_token = token.token_secret
        if not refresh_token:
            logger.warning(f"No hay refresh token para {self.user.username}")
            return

        try:
            new_token_info = sp_oauth.refresh_access_token(refresh_token)
            if new_token_info:
                token.token = new_token_info["access_token"]
                if "refresh_token" in new_token_info:
                    token.token_secret = new_token_info["refresh_token"]

                expires_in = new_token_info.get("expires_in", 3600)
                token.expires_at = timezone.now() + timezone.timedelta(seconds=expires_in)
                token.save()
                logger.info(f"Token refrescado exitosamente para {self.user.username}")
        except Exception as e:
            logger.error(f"Error al refrescar token: {e}")

    def create_playlist(self, name, description="", public=True):
        """Crea una playlist usando el ID técnico recuperado en el init."""
        if not self.client or not self.spotify_user_id:
            logger.error("No hay cliente de Spotify disponible o ID de usuario")
            return None

        try:
            res = self.client.user_playlist_create(
                user=self.spotify_user_id,
                name=name,
                public=public,
                collaborative=False,
                description=description
            )
            logger.info(f"✅ Playlist creada con éxito: {res['id']}")
            return res
        except spotipy.exceptions.SpotifyException as e:
            logger.error(f"Error de Spotify API ({e.http_status}): {e.msg}")
            return None

    def add_tracks_to_playlist(self, playlist_id, track_uris):
        if not self.client or not track_uris:
            return False
        try:
            for i in range(0, len(track_uris), 100):
                batch = track_uris[i : i + 100]
                self.client.playlist_add_items(playlist_id, batch)
            return True
        except Exception as e:
            logger.error(f"Error al añadir tracks: {e}")
            return False

    def search_tracks(self, query: str, limit: int = 20, **_kwargs):
        if not self.client: return None
        return self.client.search(q=query, limit=limit, type="track")

    def get_recommendations(self, seed_artists=None, seed_genres=None, seed_tracks=None, limit=20, **kwargs):
        if not self.client: return None
        try:
            return self.client.recommendations(seed_artists=seed_artists, seed_genres=seed_genres, seed_tracks=seed_tracks, limit=limit, **kwargs)
        except Exception as e:
            logger.error(f"Error en recomendaciones: {e}")
            return None

    def get_audio_features(self, track_ids):
        if not self.client or not track_ids: return {}
        try:
            features_dict = {}
            for i in range(0, len(track_ids), 100):
                batch = track_ids[i : i + 100]
                features = self.client.audio_features(batch)
                for f in features:
                    if f: features_dict[f["id"]] = f
            return features_dict
        except Exception as e:
            logger.error(f"Error en audio features: {e}")
            return {}

    @staticmethod
    def verify_api_connection():
        try:
            auth_manager = SpotifyClientCredentials(
                client_id=settings.SPOTIPY_CLIENT_ID,
                client_secret=settings.SPOTIPY_CLIENT_SECRET,
            )
            sp = spotipy.Spotify(auth_manager=auth_manager)
            sp.search(q="test", limit=1)
            return True, "Conexión exitosa."
        except Exception as e:
            return False, str(e)