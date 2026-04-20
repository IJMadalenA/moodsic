from django.urls import path
from .views.profile_view import profile_view
from .views.spotify_auth import spotify_auth_login, spotify_auth_callback # Importamos tus vistas

app_name = "users"

urlpatterns = [
    path("profile/", profile_view, name="profile"),
    
    # Estas líneas son las que obligan a Django a usar TU código
    path("spotify/login/", spotify_auth_login, name="spotify_login"),
    path("spotify/login/callback/", spotify_auth_callback, name="spotify_callback"),
]