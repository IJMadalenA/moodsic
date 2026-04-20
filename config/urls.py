"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path

from apps.users.views.spotify_callback import spotify_callback_redirect
from apps.users.views.spotify_auth import (
    spotify_auth_callback,
    spotify_auth_login,
)

urlpatterns = [
    path("", include("apps.dashboard.urls", namespace="dashboard")),
    path("admin/", admin.site.urls),
    path("accounts/spotify/login/", spotify_auth_login, name="spotify_login"),
    path("accounts/spotify/login/callback/", spotify_auth_callback, name="spotify_callback"),
    path("accounts/", include("apps.users.urls", namespace="users")),
    path("accounts/", include("allauth.urls")),
    path("callback", spotify_callback_redirect, name="spotify_callback_redirect"),
    path("api/interactions/", include("apps.interactions.urls")),
]
