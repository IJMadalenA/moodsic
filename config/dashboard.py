from datetime import timedelta

from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from apps.context.models import WeatherContext
from apps.music.models import MusicBriefing


def dashboard_callback(context):
    """
    Callback para personalizar el dashboard de Unfold.
    """
    # 1. Freshness del Clima
    six_hours_ago = now() - timedelta(hours=6)
    stale_weather_count = WeatherContext.objects.filter(
        timestamp__lt=six_hours_ago
    ).count()
    total_weather_count = WeatherContext.objects.count()

    # 2. Conversión de Moods (Últimas 24h)
    last_24h = now() - timedelta(days=1)
    # mood_stats = (
    #     MusicBriefing.objects.filter(created_at__gt=last_24h)
    #     .values("mood_name")
    #     .annotate(count=models.Count("id"))
    #     .order_by("-count")[:5]
    # )

    context.update(
        {
            "statistics": [
                {
                    "title": _("Clima Desactualizado (>6h)"),
                    "metric": f"{stale_weather_count}/{total_weather_count}",
                    "icon": "exclamation-circle",
                    "color": "danger" if stale_weather_count > 0 else "success",
                },
                {
                    "title": _("Total Briefings (24h)"),
                    "metric": MusicBriefing.objects.filter(
                        created_at__gt=last_24h
                    ).count(),
                    "icon": "music-note",
                    "color": "primary",
                },
            ],
        }
    )
    return context
