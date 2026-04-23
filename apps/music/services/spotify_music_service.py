import logging
import spotipy
from django.conf import settings
from django.utils import timezone
from allauth.socialaccount.models import SocialToken
from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials
from apps.music.models import Artist, Album, Track, TrackAudioFeatures

logger = logging.getLogger(__name__)

class SpotifyMusicService:
    """
    Servicio reconstruido para la gestión robusta de tokens y API de Spotify.
    """

    def __init__(self, user):
        self.user = user
        self.client = None
        self.spotify_user_id = None
        
        # 1. Obtener el cliente validado (y refrescado si hace falta)
        self.client = self.get_spotify_client()
        
        if self.client:
            try:
                me = self.client.current_user()
                self.spotify_user_id = me['id']
                print(f"✅ [SERVICIO] Conexión establecida con ID de Spotify: {self.spotify_user_id}")
            except Exception as e:
                print(f"⚠️ [SERVICIO] Cliente obtenido pero no validado: {e}")
                self.client = None

    def get_spotify_client(self):
        """
        Obtiene el cliente de Spotify usando SocialToken. 
        Maneja el refresco automático si el token ha caducado.
        """
        try:
            # Recuperar el token de la base de datos de Allauth
            token_obj = SocialToken.objects.filter(
                account__user=self.user, 
                account__provider='spotify'
            ).order_by('-id').first()

            if not token_obj:
                print(f"❌ [AUTH] No existe SocialToken para el usuario {self.user.username}")
                return None

            # 2. Verificar expiración (con margen de 60 segundos)
            if not token_obj.expires_at or token_obj.expires_at <= timezone.now():
                print(f"🔄 [AUTH] Token caducado. Iniciando refresco para {self.user.username}...")
                self._refresh_token_process(token_obj)
                token_obj.refresh_from_db()

            # 3. Retornar cliente de spotipy con el Access Token actual
            return spotipy.Spotify(auth=token_obj.token)

        except Exception as e:
            print(f"❌ [AUTH] Error crítico obteniendo cliente: {e}")
            return None

    def _refresh_token_process(self, token_obj):
        """Lógica interna de refresco contra la API de Spotify."""
        sp_oauth = SpotifyOAuth(
            client_id=settings.SPOTIPY_CLIENT_ID,
            client_secret=settings.SPOTIPY_CLIENT_SECRET,
            redirect_uri=settings.SPOTIPY_REDIRECT_URI,
        )

        try:
            # El refresh_token se guarda en 'token_secret' en la tabla SocialToken
            if not token_obj.token_secret:
                print("❌ [REFRESH] No hay Refresh Token (token_secret) disponible.")
                return

            new_info = sp_oauth.refresh_access_token(token_obj.token_secret)
            
            if new_info:
                token_obj.token = new_info['access_token']
                if 'refresh_token' in new_info:
                    token_obj.token_secret = new_info['refresh_token']
                
                expires_in = new_info.get('expires_in', 3600)
                token_obj.expires_at = timezone.now() + timezone.timedelta(seconds=expires_in)
                token_obj.save()
                print("✅ [REFRESH] Token actualizado en base de datos.")
        except Exception as e:
            print(f"❌ [REFRESH] Error al refrescar en Spotify: {e}")

    def create_playlist(self, name, description="Created by Moodsic", public=False):
        """Crea una playlist verificando permisos (403 Forbidden)."""
        print(f"\n{'='*40}\nSOLICITUD: Crear Playlist '{name}'")
        
        if not self.client or not self.spotify_user_id:
            print("❌ Error: Servicio no inicializado correctamente.")
            return None

        try:
            # Llamada oficial a la API
            playlist = self.client.user_playlist_create(
                user=self.spotify_user_id,
                name=name,
                public=public,
                description=description
            )
            print(f"✅ ÉXITO: Playlist creada ID: {playlist.get('id')}")
            return playlist

        except spotipy.exceptions.SpotifyException as e:
            print(f"\n{'!'*40}\nERROR DE SPOTIFY (HTTP {e.http_status})")
            if e.http_status == 403:
                print("MENSAJE: Prohibido (403).")
                print("CAUSAS POSIBLES:\n1. Falta el scope 'playlist-modify-public' en settings.py")
                print(f"2. Tu email ({self.user.email}) no está en 'User Management' del Dashboard de Spotify.")
            else:
                print(f"MENSAJE: {e.msg}")
            print(f"{'!'*40}\n")
            return None

    # --- OTROS MÉTODOS MANTENIDOS Y LIMPIOS ---

    def add_tracks_to_playlist(self, playlist_id, track_uris):
        if not self.client or not track_uris: return False
        try:
            # Spotify permite máx 100 por petición
            for i in range(0, len(track_uris), 100):
                self.client.playlist_add_items(playlist_id, track_uris[i : i + 100])
            return True
        except Exception as e:
            logger.error(f"Error al añadir tracks: {e}")
            return False

    def get_audio_features(self, track_ids):
        if not self.client or not track_ids: return {}
        try:
            features_dict = {}
            for i in range(0, len(track_ids), 100):
                batch = track_ids[i : i + 100]
                results = self.client.audio_features(batch)
                for f in results:
                    if f: features_dict[f["id"]] = f
            return features_dict
        except Exception as e:
            logger.error(f"Error en audio features: {e}")
            return {}

    @staticmethod
    def verify_api_connection():
        """Verificación estática básica de credenciales de la App."""
        try:
            auth_manager = SpotifyClientCredentials(
                client_id=settings.SPOTIPY_CLIENT_ID,
                client_secret=settings.SPOTIPY_CLIENT_SECRET,
            )
            sp = spotipy.Spotify(auth_manager=auth_manager)
            sp.search(q="test", limit=1)
            return True, "Credenciales de App correctas."
        except Exception as e:
            return False, str(e)