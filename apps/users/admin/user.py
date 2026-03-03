from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from unfold.admin import ModelAdmin

from apps.users.models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    """
    Custom UserAdmin using Unfold design.
    """

    fieldsets = (
        *BaseUserAdmin.fieldsets,
        (
            "Spotify info",
            {"fields": ("spotify_id", "avatar_url", "is_spotify_connected")},
        ),
    )
    list_display = (*BaseUserAdmin.list_display, "spotify_id", "is_spotify_connected")
    search_fields = (*BaseUserAdmin.search_fields, "spotify_id")
