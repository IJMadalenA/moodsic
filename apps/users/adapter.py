from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class MoodsicSocialAccountAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        """
        Saves a newly signed up social login user and populates Spotify fields.
        """
        user = super().save_user(request, sociallogin, form)

        # Populate custom fields directly on the Custom User model
        user.avatar_url = sociallogin.account.get_avatar_url()
        user.spotify_id = sociallogin.account.uid
        user.is_spotify_connected = True
        user.save()

        return user
