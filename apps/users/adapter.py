import logging
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

logger = logging.getLogger(__name__)


class MoodsicSocialAccountAdapter(DefaultSocialAccountAdapter):
    def on_authentication_error(
        self,
        request,
        provider,
        error=None,
        exception=None,
        extra_context=None,
    ):
        logger.error(
            "OAuth authentication error provider=%s error=%s exception=%r extra_context=%r",
            getattr(provider, "id", provider),
            error,
            exception,
            extra_context,
            exc_info=True,
        )

    def save_user(self, request, sociallogin, form=None):
        """
        Saves a newly signed up social login user and populates Spotify fields.
        """
        try:
            user = super().save_user(request, sociallogin, form)
            logger.info(f"✓ User created/updated: {user.email}")

            # Populate custom fields directly on the Custom User model
            avatar_url = sociallogin.account.get_avatar_url()
            logger.info(f"Avatar URL from Spotify: {avatar_url}")
            
            user.avatar_url = avatar_url or ""
            user.spotify_id = sociallogin.account.uid
            user.is_spotify_connected = True
            
            logger.info(f"Setting spotify_id={user.spotify_id}, avatar_url={user.avatar_url}")
            user.save()
            logger.info(f"✓ Spotify fields saved successfully")

            return user
        except Exception as e:
            logger.error(f"✗ ERROR in save_user: {type(e).__name__}: {str(e)}", exc_info=True)
            raise
