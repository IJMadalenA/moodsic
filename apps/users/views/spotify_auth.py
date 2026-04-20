from allauth.socialaccount.adapter import get_adapter
from allauth.socialaccount.providers.spotify.views import SpotifyOAuth2Adapter
from allauth.socialaccount.providers.oauth2.views import OAuth2CallbackView, OAuth2LoginView
from allauth.socialaccount.providers.base import ProviderException
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model

User = get_user_model()

class MoodsicSpotifyOAuth2Adapter(SpotifyOAuth2Adapter):
    """Adaptador personalizado de Spotify para Moodsic."""

    def complete_login(self, request, app, token, **kwargs):
        # Este print aparecerá en tu terminal de VS Code al volver de Spotify
        print("-" * 30)
        print("🚀 PROCESANDO LOGIN EN SPOTIFY...")
        
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
            
            extra_data = resp.json()

        # Generamos el objeto de login de Allauth
        login = self.get_provider().sociallogin_from_response(request, extra_data)
        
        # --- LÓGICA DE PERSISTENCIA EN EL MODELO USER ---
        # 1. Intentamos obtener el usuario actual de la sesión
        user = request.user
        
        # 2. Si no está autenticado (a veces pasa en el callback), buscamos por email
        if not user.is_authenticated:
            email = extra_data.get('email')
            user = User.objects.filter(email=email).first()

        if user:
            # 1. El Access Token está bien
            user.access_token = token.token
            
            # 2. CORRECCIÓN AQUÍ: En OAuth2 de Spotify, el refresh token 
            # suele venir en token.token_secret o simplemente token.refresh_token
            # Vamos a intentar capturarlo de ambas formas:
            rt = getattr(token, 'token_secret', None) or getattr(token, 'refresh_token', None)
            user.refresh_token = rt
            
            # 3. Guardamos la expiración
            if hasattr(token, 'expires_at') and token.expires_at:
                user.token_expires_at = token.expires_at
            else:
                user.token_expires_at = timezone.now() + timedelta(seconds=3600)
            
            user.is_spotify_connected = True
            user.spotify_id = extra_data.get('id')
            
            images = extra_data.get('images', [])
            if images:
                user.avatar_url = images[0].get('url', '')

            user.save()
            
            # Cambiamos el print para no confundirnos
            print(f"✅ TOKEN ACTUALIZADO: {user.username} ya tiene permisos de ESCRITURA.")
            print(f"DEBUG: Refresh Token guardado: {bool(rt)}")
        else:
            print("❌ ERROR: No se pudo encontrar al usuario para guardar los tokens.")
        
        print("-" * 30)
        return login

# Estas son las vistas que llamamos desde config/urls.py
spotify_auth_login = OAuth2LoginView.adapter_view(MoodsicSpotifyOAuth2Adapter)
spotify_auth_callback = OAuth2CallbackView.adapter_view(MoodsicSpotifyOAuth2Adapter)