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

    def get_playlist_tracks(self, playlist_id, limit=50):
        """
        Obtiene los tracks de una playlist específica.
        
        Args:
            playlist_id: ID de la playlist de Spotify (puede incluir 'spotify:playlist:')
            limit: Número máximo de tracks a obtener (default: 50, max: 50)
        
        Returns:
            Lista de diccionarios con información de tracks
        """
        if not self.client:
            logger.warning(f"No Spotify client available for user {self.user.username}")
            return []
        
        # Limpiar playlist_id si tiene el formato spotify:playlist:xxx
        if playlist_id.startswith("spotify:playlist:"):
            playlist_id = playlist_id.split(":")[-1]
        
        try:
            results = self.client.playlist_tracks(playlist_id, limit=min(limit, 50))
            tracks = []
            
            for item in results.get("items", []):
                track = item.get("track", {})
                if track:
                    tracks.append({
                        "id": track.get("id"),
                        "name": track.get("name"),
                        "artists": [artist.get("name") for artist in track.get("artists", [])],
                        "album": track.get("album", {}).get("name"),
                        "album_id": track.get("album", {}).get("id"),
                        "duration_ms": track.get("duration_ms"),
                        "explicit": track.get("explicit", False),
                        "popularity": track.get("popularity"),
                        "uri": track.get("uri"),
                        "preview_url": track.get("preview_url"),
                    })
            
            logger.info(f"Retrieved {len(tracks)} tracks from playlist {playlist_id}")
            return tracks
        except Exception as e:
            logger.error(f"Error retrieving playlist tracks: {e}")
            return []
    
    def get_user_liked_tracks(self, limit=50):
        """
        Obtiene los tracks que le gustan al usuario (Liked Songs).
        
        Args:
            limit: Número máximo de tracks a obtener
        
        Returns:
            Lista de diccionarios con información de tracks
        """
        if not self.client:
            logger.warning(f"No Spotify client available for user {self.user.username}")
            return []
        
        try:
            results = self.client.current_user_saved_tracks(limit=min(limit, 50))
            tracks = []
            
            for item in results.get("items", []):
                track = item.get("track", {})
                if track:
                    tracks.append({
                        "id": track.get("id"),
                        "name": track.get("name"),
                        "artists": [artist.get("name") for artist in track.get("artists", [])],
                        "album": track.get("album", {}).get("name"),
                        "album_id": track.get("album", {}).get("id"),
                        "duration_ms": track.get("duration_ms"),
                        "explicit": track.get("explicit", False),
                        "popularity": track.get("popularity"),
                        "uri": track.get("uri"),
                        "preview_url": track.get("preview_url"),
                    })
            
            logger.info(f"Retrieved {len(tracks)} liked tracks for user {self.user.username}")
            return tracks
        except Exception as e:
            logger.error(f"Error retrieving user liked tracks: {e}")
            return []
    
    def get_top_tracks(self, time_range="medium_term", limit=50):
        """
        Obtiene los top tracks del usuario según Spotify.
        
        Args:
            time_range: 'long_term' (años), 'medium_term' (6 meses), 'short_term' (4 semanas)
            limit: Número máximo de tracks a obtener
        
        Returns:
            Lista de diccionarios con información de tracks
        """
        if not self.client:
            logger.warning(f"No Spotify client available for user {self.user.username}")
            return []
        
        try:
            results = self.client.current_user_top_tracks(
                time_range=time_range, 
                limit=min(limit, 50)
            )
            tracks = []
            
            for track in results.get("items", []):
                tracks.append({
                    "id": track.get("id"),
                    "name": track.get("name"),
                    "artists": [artist.get("name") for artist in track.get("artists", [])],
                    "album": track.get("album", {}).get("name"),
                    "album_id": track.get("album", {}).get("id"),
                    "duration_ms": track.get("duration_ms"),
                    "explicit": track.get("explicit", False),
                    "popularity": track.get("popularity"),
                    "uri": track.get("uri"),
                    "preview_url": track.get("preview_url"),
                })
            
            logger.info(f"Retrieved {len(tracks)} top tracks for user {self.user.username}")
            return tracks
        except Exception as e:
            logger.error(f"Error retrieving top tracks: {e}")
            return []
    
    def create_playlist(self, name, description="", public=False):
        """
        Crea una nueva playlist en la cuenta de Spotify del usuario.
        
        Args:
            name: Nombre de la playlist
            description: Descripción de la playlist
            public: Si la playlist es pública
        
        Returns:
            Diccionario con información de la playlist creada, o None en caso de error
        """
        if not self.client:
            logger.warning(f"No Spotify client available for user {self.user.username}")
            return None
        
        try:
            user_id = self.client.current_user().get("id")
            if not user_id:
                logger.error("Could not get Spotify user ID")
                return None
            
            playlist = self.client.user_playlist_create(
                user=user_id,
                name=name,
                public=public,
                description=description,
            )
            
            logger.info(f"Created playlist '{name}' for user {self.user.username}")
            return {
                "id": playlist.get("id"),
                "name": playlist.get("name"),
                "spotify_id": playlist.get("id"),
                "uri": playlist.get("uri"),
                "external_urls": playlist.get("external_urls", {}).get("spotify"),
                "snapshot_id": playlist.get("snapshot_id"),
                "images": playlist.get("images", []),
            }
        except Exception as e:
            logger.error(f"Error creating playlist: {e}")
            return None
    
    def add_tracks_to_playlist(self, playlist_id, track_uris):
        """
        Agrega tracks a una playlist existente.
        
        Args:
            playlist_id: ID de la playlist
            track_uris: Lista de URIs de Spotify (spotify:track:xxx)
        
        Returns:
            True si fue exitoso, False en caso de error
        """
        if not self.client:
            logger.warning(f"No Spotify client available for user {self.user.username}")
            return False
        
        if not track_uris:
            logger.warning("No tracks provided to add to playlist")
            return False
        
        try:
            # Spotify API tiene límite de 100 tracks por request
            for i in range(0, len(track_uris), 100):
                batch = track_uris[i:i+100]
                self.client.playlist_add_items(playlist_id, batch)
            
            logger.info(f"Added {len(track_uris)} tracks to playlist {playlist_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding tracks to playlist: {e}")
            return False
    
    def get_audio_features(self, track_ids):
        """
        Obtiene características de audio para una lista de tracks.
        
        Args:
            track_ids: Lista de IDs de Spotify
        
        Returns:
            Diccionario mapping track_id -> audio features
        """
        if not self.client:
            logger.warning(f"No Spotify client available for user {self.user.username}")
            return {}
        
        if not track_ids:
            return {}
        
        try:
            features_dict = {}
            # Spotify API permite máximo 100 tracks por request
            for i in range(0, len(track_ids), 100):
                batch = track_ids[i:i+100]
                features = self.client.audio_features(batch)
                
                for feature in features:
                    if feature:
                        features_dict[feature["id"]] = {
                            "danceability": feature.get("danceability", 0),
                            "energy": feature.get("energy", 0),
                            "key": feature.get("key", 0),
                            "loudness": feature.get("loudness", 0),
                            "mode": feature.get("mode", 0),
                            "speechiness": feature.get("speechiness", 0),
                            "acousticness": feature.get("acousticness", 0),
                            "instrumentalness": feature.get("instrumentalness", 0),
                            "liveness": feature.get("liveness", 0),
                            "valence": feature.get("valence", 0),
                            "tempo": feature.get("tempo", 0),
                            "time_signature": feature.get("time_signature", 0),
                        }
            
            logger.info(f"Retrieved audio features for {len(features_dict)} tracks")
            return features_dict
        except Exception as e:
            logger.error(f"Error retrieving audio features: {e}")
            return {}

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
