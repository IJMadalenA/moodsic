from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom User model for Moodsic.
    Inherits from Django's AbstractUser to maintain standard functionality
    while allowing for expansion of profile-specific fields.
    """

    spotify_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    avatar_url = models.URLField(max_length=500, blank=True, default="")

    # Optional fields for analytics or user-specific settings
    is_spotify_connected = models.BooleanField(default=False)

    class Meta:
        db_table = "auth_user_custom"
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return self.email if self.email else self.username
