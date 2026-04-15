"""
API Endpoints para Interactions usando Django-Ninja.
"""

import logging
from collections import Counter
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count, Sum
from django.utils import timezone
from ninja import Router
from ninja.responses import Response

from apps.interactions.models import Interaction, InteractionSession
from apps.interactions.schemas import (
    DashboardMetricsSchema,
    InteractionCreateSchema,
    InteractionResponseSchema,
    SessionStatsSchema,
    UserStatsSchema,
)
from apps.interactions.services.playlist_generation_service import (
    get_playlist_generation_service,
)
from apps.music.models import Track

logger = logging.getLogger(__name__)

User = get_user_model()

router = Router()


@router.post(
    "/interactions/",
    response=InteractionResponseSchema,
    tags=["interactions"],
)
def create_interaction(request, payload: InteractionCreateSchema):
    """
    Crea un registro de interacción usuario-track.

    **Campos:**
    - track_id: ID del track
    - feedback: 'completed', 'skip', 'skip_immediate', 'replay', 'added_to_playlist'
    - play_duration: Segundos reproducidos
    - track_duration: Duración total del track
    - session_id: ID de la sesión (opcional)

    **Retorna:** InteractionResponseSchema
    """
    if not request.user.is_authenticated:
        return Response(
            {
                "error": "Autenticación requerida",
                "message": "Inicia sesión para registrar interacciones del usuario.",
            },
            status=401,
        )

    try:
        track = Track.objects.get(id=payload.track_id)
    except Track.DoesNotExist:
        return Response(
            {
                "error": "Track no encontrado",
                "message": "El track indicado no existe en el catálogo local.",
            },
            status=404,
        )

    service = get_playlist_generation_service()

    try:
        result = service.record_interaction(
            user=request.user,
            track=track,
            feedback=payload.feedback,
            play_duration=payload.play_duration,
            track_duration=payload.track_duration,
            session_id=payload.session_id,
            weather_id=payload.weather_id,
            news_ids=payload.news_ids,
        )

        interaction = Interaction.objects.get(id=result["interaction_id"])
    except ValueError as exc:
        logger.warning("Interacción rechazada: %s", exc)
        return Response(
            {
                "error": "No se pudo registrar la interacción",
                "message": str(exc),
            },
            status=400,
        )
    except Exception as exc:
        logger.error("Error inesperado registrando interacción: %s", exc, exc_info=True)
        return Response(
            {
                "error": "Error interno registrando la interacción",
                "message": "Vuelve a intentarlo en unos segundos.",
            },
            status=500,
        )

    return {
        "id": interaction.id,
        "user_id": interaction.user_id,
        "track_id": interaction.track_id,
        "feedback": interaction.feedback,
        "reward": interaction.reward,
        "completion_percentage": interaction.completion_percentage,
        "is_positive": interaction.is_positive,
        "started_at": interaction.started_at.isoformat(),
        "created_at": interaction.created_at.isoformat(),
    }


@router.get(
    "/interactions/user/stats/",
    response=UserStatsSchema,
    tags=["interactions"],
)
def get_user_stats(request):
    """
    Obtiene estadísticas del usuario autenticado.

    **Retorna:** UserStatsSchema con:
    - total_interactions
    - skip_rate
    - completion_rate
    - average_reward
    - favorite_genres
    - favorite_artists
    """
    if not request.user.is_authenticated:
        return Response(
            {
                "error": "Autenticación requerida",
                "message": "Inicia sesión para consultar tus estadísticas.",
            },
            status=401,
        )

    service = get_playlist_generation_service()
    return service.get_user_stats(request.user)


@router.get(
    "/interactions/session/{session_id}/stats/",
    response=SessionStatsSchema,
    tags=["interactions"],
)
def get_session_stats(request, session_id: str):
    """
    Obtiene estadísticas de una sesión específica.

    **Parámetros:**
    - session_id: ID de la sesión

    **Retorna:** SessionStatsSchema
    """
    if not request.user.is_authenticated:
        return Response(
            {
                "error": "Autenticación requerida",
                "message": "Inicia sesión para consultar sesiones guardadas.",
            },
            status=401,
        )

    try:
        session = InteractionSession.objects.get(session_id=session_id)
    except InteractionSession.DoesNotExist:
        return Response(
            {
                "error": "Sesión no encontrada",
                "message": "No existe ninguna sesión con el identificador indicado.",
            },
            status=404,
        )

    # Calcular métricas
    session.calculate_metrics()

    skip_rate = (
        session.skip_count / session.total_tracks
        if session.total_tracks > 0
        else 0.0
    )
    completion_rate = (
        session.completed_count / session.total_tracks
        if session.total_tracks > 0
        else 0.0
    )

    return {
        "session_id": session.session_id,
        "total_tracks": session.total_tracks,
        "skip_count": session.skip_count,
        "completed_count": session.completed_count,
        "average_reward": session.average_reward,
        "total_reward": session.total_reward,
        "skip_rate": skip_rate,
        "completion_rate": completion_rate,
        "started_at": session.started_at.isoformat(),
        "is_active": session.is_active,
    }


@router.get(
    "/dashboard/metrics/",
    response=DashboardMetricsSchema,
    tags=["dashboard"],
)
def get_dashboard_metrics(request):
    """
    Obtiene métricas del dashboard para administradores.

    **Retorna:** DashboardMetricsSchema con:
    - total_users
    - total_interactions
    - average_skip_rate
    - average_completion_rate
    - top_tracks
    """
    if not request.user.is_authenticated:
        return Response(
            {
                "error": "Autenticación requerida",
                "message": "Inicia sesión como administrador para ver este panel.",
            },
            status=401,
        )

    if not request.user.is_staff:
        return Response(
            {
                "error": "Permiso denegado",
                "message": "Este endpoint solo está disponible para personal del proyecto.",
            },
            status=403,
        )

    # Agregaciones
    total_interactions = Interaction.objects.count()
    total_users = User.objects.filter(interactions__isnull=False).distinct().count()

    # Skip rate promedio
    avg_skip_rate = (
        Interaction.objects.filter(feedback__startswith="skip").count()
        / total_interactions
        if total_interactions > 0
        else 0.0
    )

    # Completion rate promedio
    avg_completion_rate = (
        Interaction.objects.filter(feedback="completed").count()
        / total_interactions
        if total_interactions > 0
        else 0.0
    )

    # Total reward generado
    total_reward = Interaction.objects.aggregate(
        total=Sum("reward")
    )["total"] or 0.0

    # Active sessions
    active_sessions = InteractionSession.objects.filter(is_active=True).count()

    # Top tracks
    top_tracks = (
        Interaction.objects.values("track__name")
        .annotate(count=Count("id"))
        .order_by("-count")[:5]
    )

    start_date = timezone.now().date() - timedelta(days=6)
    growth_data = (
        Interaction.objects
        .filter(created_at__date__gte=start_date)
        .values("created_at__date")
        .annotate(
            new_users=Count("user", distinct=True),
            interactions=Count("id"),
        )
        .order_by("created_at__date")
    )

    growth_map = {
        item["created_at__date"]: item for item in growth_data
    }

    user_growth = []
    for offset in range(7):
        day = start_date + timedelta(days=offset)
        item = growth_map.get(day, {})
        user_growth.append({
            "date": day.isoformat(),
            "new_users": item.get("new_users", 0),
            "interactions": item.get("interactions", 0),
        })

    return {
        "total_users": total_users,
        "total_interactions": total_interactions,
        "average_skip_rate": avg_skip_rate,
        "average_completion_rate": avg_completion_rate,
        "total_reward_generated": float(total_reward),
        "active_sessions": active_sessions,
        "top_tracks": list(top_tracks),
        "user_growth": user_growth,
    }


def _get_favorite_artists(user):
    """Retorna los artistas preferidos del usuario según sus interacciones."""
    artist_counts = (
        Interaction.objects.filter(user=user)
        .values("track__artists__name")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    return [item["track__artists__name"] for item in artist_counts if item["track__artists__name"]][:5]


def _get_favorite_genres(user):
    """Retorna los géneros favoritos del usuario según los artistas de sus tracks."""
    genres_counter = Counter()
    interactions = Interaction.objects.filter(user=user).select_related("track").prefetch_related("track__artists")

    for interaction in interactions:
        for artist in interaction.track.artists.all():
            for genre in getattr(artist, "genres", []) or []:
                normalized_genre = genre.strip()
                if normalized_genre:
                    genres_counter[normalized_genre] += 1

    return [genre for genre, _ in genres_counter.most_common(5)]


def _get_average_session_length(user):
    """Calcula la longitud promedio de las sesiones de usuario en segundos."""
    sessions = InteractionSession.objects.filter(user=user, ended_at__isnull=False)
    durations = [
        (session.ended_at - session.started_at).total_seconds()
        for session in sessions
        if session.ended_at
    ]

    if not durations:
        return 0.0

    return float(sum(durations) / len(durations))
