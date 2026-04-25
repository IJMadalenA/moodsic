from django.conf import settings
from django.shortcuts import render

from apps.context.models import NewsContext, WeatherContext
from apps.interactions.models import Interaction, InteractionSession
from apps.music.models import Playlist, Track


def dashboard_home(request):
    """Vista ligera de demo para profesores y equipo."""
    total_interactions = Interaction.objects.count()
    total_playlists = Playlist.objects.count()
    total_tracks = Track.objects.count()
    active_sessions = InteractionSession.objects.filter(is_active=True).count()

    skip_count = Interaction.objects.filter(feedback__startswith="skip").count()
    skip_rate = (
        round((skip_count / total_interactions) * 100, 1) if total_interactions else 0.0
    )

    integration_status = [
        {
            "name": "Modo offline reproducible",
            "status": "listo",
            "detail": "Seeds sintéticos, evaluación y benchmark disponibles.",
        },
        {
            "name": "Spotify real",
            "status": "pendiente" if not settings.SPOTIPY_CLIENT_ID else "configurado",
            "detail": "La integración está preparada, pero la validación final depende de credenciales reales.",
        },
        {
            "name": "Noticias externas",
            "status": "configurado" if settings.NEWSAPI_KEY else "fallback local",
            "detail": "Si la API no está disponible, el sistema usa noticias en caché.",
        },
    ]

    return render(
        request,
        "dashboard/home.html",
        {
            "stats": {
                "playlists": total_playlists,
                "tracks": total_tracks,
                "interactions": total_interactions,
                "active_sessions": active_sessions,
                "skip_rate": skip_rate,
                "weather_records": WeatherContext.objects.count(),
                "news_records": NewsContext.objects.count(),
            },
            "recent_playlists": Playlist.objects.select_related("user").order_by(
                "-created_at"
            )[:5],
            "integration_status": integration_status,
        },
    )
