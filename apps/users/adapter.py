import logging

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings

logger = logging.getLogger(__name__)


class MoodsicSocialAccountAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        try:
            # 1. Ejecutamos el guardado estándar
            user = super().save_user(request, sociallogin, form)

            # SEGURIDAD: Si por alguna razón el user no tiene ID (no se guardó), lo forzamos
            if not user.pk:
                user.save()

            social_account = sociallogin.account
            token_data = sociallogin.token

            # --- LOGS DE TOKENS (Lo que pediste ver) ---
            if token_data:
                # Mostramos los primeros 40 caracteres para confirmar que es un token real
                token_data.token[:40] if token_data.token else "N/A"
                (token_data.token_secret[:20] if token_data.token_secret else "N/A")
            else:
                pass

            # 2. Guardamos en tu modelo User personalizado
            user.is_spotify_connected = True
            user.access_token = (token_data.token or "") if token_data else ""
            user.refresh_token = (token_data.token_secret or "") if token_data else ""

            # Extraemos spotify_id y avatar_url
            user.spotify_id = social_account.uid
            user.avatar_url = social_account.get_avatar_url() or ""

            if token_data and token_data.expires_at:
                user.token_expires_at = token_data.expires_at

            # 3. ASIGNACIÓN AUTOMÁTICA DE PERMISOS DE ADMIN
            # Comprobamos si el email está en la lista de ADMINS de settings.py
            is_admin_configured = False
            for admin_entry in getattr(settings, "ADMINS", []):
                if isinstance(admin_entry, (list, tuple)) and len(admin_entry) >= 2:
                    if user.email == admin_entry[1]:
                        is_admin_configured = True
                        break
                elif isinstance(admin_entry, str):
                    if ":" in admin_entry:
                        email_part = admin_entry.split(":")[1].strip()
                        if user.email == email_part:
                            is_admin_configured = True
                            break
                    elif user.email == admin_entry.strip():
                        is_admin_configured = True
                        break

            if is_admin_configured:
                user.is_staff = True
                user.is_superuser = True

            user.save()

            # 4. VINCULACIÓN CON TABLAS SOCIALES (ADMIN)
            # Esto es lo que rellena "Social Accounts"
            social_account.user = user
            social_account.save()

            # Esto es lo que rellena "Social Application Tokens"
            if token_data:
                token_data.account = social_account
                token_data.save()

            return user

        except Exception as e:
            logger.error(f"Fallo en save_user: {e}", exc_info=True)
            raise
