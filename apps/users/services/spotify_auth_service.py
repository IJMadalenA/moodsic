import spotipy
from spotipy.oauth2 import SpotifyOAuth
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

class SpotifyAuthService:
    """
    Servicio encargado de gestionar la comunicación con la API de Spotify
    utilizando el protocolo OAuth2.
    
    Responsabilidades:
    1. Generar la URL de autorización para el usuario.
    2. Intercambiar el código de autorización por tokens (Access y Refresh).
    3. Refrescar tokens expirados de forma automática.
    """

    def __init__(self):
        # Configuramos el objeto OAuth de Spotipy con las credenciales del .env
        self.sp_oauth = SpotifyOAuth(
            client_id=settings.SPOTIPY_CLIENT_ID,
            client_secret=settings.SPOTIPY_CLIENT_SECRET,
            redirect_uri=settings.SPOTIPY_REDIRECT_URI,
            # Scopes necesarios para que MOODSIC funcione:
            # - user-read-recently-played: Para que el modelo de ML sepa qué escuchaste.
            # - playlist-modify-public: Para crear y editar las playlists generadas.
            # - user-library-read: Para conocer tus gustos generales.
            scope="user-library-read user-read-recently-played playlist-modify-public"
        )

    def get_auth_url(self):
        """
        Genera la URL oficial de Spotify donde el usuario debe iniciar sesión
        y aceptar los permisos solicitados por MOODSIC.
        """
        return self.sp_oauth.get_authorize_url()

    def get_tokens_from_code(self, code):
        """
        Intercambia el código temporal que nos da Spotify tras el login
        por un diccionario que contiene access_token, refresh_token y expires_in.
        """
        return self.sp_oauth.get_access_token(code)

    @staticmethod
    def save_user_tokens(user, token_info):
        """
        Persiste los tokens recibidos en nuestro modelo de usuario personalizado.
        
        Args:
            user: Instancia del modelo User (custom).
            token_info: Diccionario devuelto por Spotify con los tokens.
        """
        user.access_token = token_info['access_token']
        user.refresh_token = token_info['refresh_token']
        
        # Calculamos la fecha exacta de expiración (ahora + segundos de vida del token)
        user.token_expires_at = timezone.now() + timedelta(seconds=token_info['expires_in'])
        
        user.is_spotify_connected = True
        user.save()

    def refresh_token_if_needed(self, user):
        """
        Verifica si el token ha expirado. Si es así, pide uno nuevo a Spotify
        usando el refresh_token almacenado.
        
        Este método es CRÍTICO para que el agente de RL pueda trabajar en 
        segundo plano sin que el usuario esté logueado.
        """
        # Margen de seguridad de 1 minuto antes de la expiración real
        if timezone.now() >= (user.token_expires_at - timedelta(minutes=1)):
            new_token_info = self.sp_oauth.refresh_access_token(user.refresh_token)
            
            # Actualizamos los campos en la BD con la nueva información
            user.access_token = new_token_info['access_token']
            # Spotify a veces devuelve un nuevo refresh_token, otras veces mantiene el mismo
            if 'refresh_token' in new_token_info:
                user.refresh_token = new_token_info['refresh_token']
            
            user.token_expires_at = timezone.now() + timedelta(seconds=new_token_info['expires_in'])
            user.save()
            return True
        return False