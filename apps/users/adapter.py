import logging
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)

class MoodsicSocialAccountAdapter(DefaultSocialAccountAdapter):
    def on_authentication_error(self, request, provider, error=None, exception=None, extra_context=None):
        logger.error(
            "OAuth authentication error provider=%s error=%s exception=%r extra_context=%r",
            getattr(provider, "id", provider), error, exception, extra_context, exc_info=True,
        )

    def save_user(self, request, sociallogin, form=None):
        """
        Guarda el usuario y mapea los tokens de Spotify a nuestro modelo custom.
        """
        try:
            # 1. Llamamos al guardado base de allauth
            user = super().save_user(request, sociallogin, form)
            logger.info(f"✓ User created/updated: {user.email}")

            # 2. Extraemos los datos de la cuenta social
            social_account = sociallogin.account
            token_data = sociallogin.token # Aquí están las llaves para la API
            
            # 3. Poblamos los campos de perfil
            user.avatar_url = social_account.get_avatar_url() or ""
            user.spotify_id = social_account.uid
            user.is_spotify_connected = True

            # 4. GUARDADO DE TOKENS (Crucial para el modelo de ML)
            # El access_token es lo que usamos para las llamadas inmediatas
            user.access_token = token_data.token
            
            # El refresh_token es lo que usará nuestro ml/agent.py para no pedir login de nuevo
            user.refresh_token = token_data.token_secret
            
            # Guardamos cuándo expira (Spotify suele dar 3600 segundos)
            if token_data.expires_at:
                user.token_expires_at = token_data.expires_at
            
            logger.info(f"Setting spotify_id={user.spotify_id}, access_token saved (len: {len(user.access_token)})")
            
            user.save()
            logger.info(f"✓ Spotify tokens and profile saved successfully")

            return user
            
        except Exception as e:
            logger.error(f"✗ ERROR in save_user: {type(e).__name__}: {str(e)}", exc_info=True)
            raise