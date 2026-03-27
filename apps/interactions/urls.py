"""
URLs para el app interactions.
"""

from django.urls import path
from ninja import NinjaAPI

from apps.interactions.views.api import router as interactions_router
from apps.interactions.views.playlist_api import router as playlist_router

app_name = "interactions"

# Crear API principal
api = NinjaAPI(title="Moodsic API - Interactions", version="1.0.0")

# Registrar routers
api.add_router("", interactions_router, tags=["interactions"])
api.add_router("", playlist_router, tags=["playlists"])

urlpatterns = [
    path("", api.urls),
]
