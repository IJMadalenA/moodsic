import logging
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.utils import timezone

logger = logging.getLogger(__name__)

class MoodsicSocialAccountAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        try:
            print("--- DEBUG ADAPTER: Inicio del proceso de guardado ---")
            
            # 1. Ejecutamos el guardado estándar
            user = super().save_user(request, sociallogin, form)
            
            # SEGURIDAD: Si por alguna razón el user no tiene ID (no se guardó), lo forzamos
            if not user.pk:
                user.save()
                print("--- DEBUG ADAPTER: Usuario forzado a base de datos para obtener ID ---")

            social_account = sociallogin.account
            token_data = sociallogin.token 

            # --- LOGS DE TOKENS (Lo que pediste ver) ---
            if token_data:
                # Mostramos los primeros 40 caracteres para confirmar que es un token real
                print(f"--- [TOKEN ACCESS]: {token_data.token[:40]}... ---")
                print(f"--- [TOKEN REFRESH]: {token_data.token_secret[:20]}... ---")
                print(f"--- [TOKEN EXPIRES]: {token_data.expires_at} ---")
            else:
                print("--- ⚠️ WARNING: Spotify NO envió token_data ---")

            # 2. Guardamos en tu modelo User personalizado
            user.is_spotify_connected = True
            user.access_token = token_data.token if token_data else ""
            user.refresh_token = token_data.token_secret if token_data else ""
            
            if token_data and token_data.expires_at:
                user.token_expires_at = token_data.expires_at
            
            user.save()
            print(f"--- DEBUG: Modelo User actualizado para {user.username} ---")

            # 3. VINCULACIÓN CON TABLAS SOCIALES (ADMIN)
            # Esto es lo que rellena "Social Accounts"
            social_account.user = user
            social_account.save() 
            print(f"--- DEBUG: SocialAccount vinculada con éxito (ID: {social_account.id}) ---")
            
            # Esto es lo que rellena "Social Application Tokens"
            if token_data:
                token_data.account = social_account
                token_data.save()
                print(f"--- DEBUG: SocialToken vinculado con éxito (ID: {token_data.id}) ---")
            
            return user
            
        except Exception as e:
            print(f"--- ❌ ERROR CRÍTICO EN ADAPTER: {str(e)} ---")
            logger.error(f"Fallo en save_user: {e}", exc_info=True)
            raise