"""
Configuración del Admin para el app interactions.
"""

from django.contrib import admin

from apps.interactions.models import Interaction, InteractionSession


@admin.register(Interaction)
class InteractionAdmin(admin.ModelAdmin):
    """
    Admin para registros de interacción usuario-track.
    """

    list_display = (
        "user",
        "track",
        "feedback",
        "reward",
        "completion_percentage",
        "started_at",
    )
    list_filter = (
        "feedback",
        "is_positive",
        "started_at",
        ("user", admin.RelatedOnlyFieldListFilter),
    )
    search_fields = (
        "user__username",
        "track__name",
        "session_id",
    )
    readonly_fields = (
        "user",
        "track",
        "started_at",
        "updated_at",
        "completion_percentage",
        "is_positive",
    )
    fieldsets = (
        (
            "Información de Interacción",
            {
                "fields": (
                    "user",
                    "track",
                    "feedback",
                    "session_id",
                )
            },
        ),
        (
            "Contexto",
            {
                "fields": (
                    "weather_id",
                    "news_ids",
                    "playlist_id",
                )
            },
        ),
        (
            "Métricas",
            {
                "fields": (
                    "reward",
                    "play_duration",
                    "track_duration",
                    "completion_percentage",
                    "is_positive",
                )
            },
        ),
        (
            "Tiempo",
            {
                "fields": (
                    "started_at",
                    "ended_at",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    def has_add_permission(self, request):
        # Las interacciones se crean automáticamente via API
        return True

    def has_delete_permission(self, request, obj=None):
        # Permitir delete pero es raro que se necesite
        return True


@admin.register(InteractionSession)
class InteractionSessionAdmin(admin.ModelAdmin):
    """
    Admin para sesiones de interacción.
    """

    list_display = (
        "session_id",
        "user",
        "total_tracks",
        "skip_count",
        "completed_count",
        "average_reward",
        "started_at",
        "is_active",
    )
    list_filter = (
        "is_active",
        "started_at",
        ("user", admin.RelatedOnlyFieldListFilter),
    )
    search_fields = (
        "session_id",
        "user__username",
    )
    readonly_fields = (
        "session_id",
        "started_at",
        "created_at",
        "updated_at",
    )

    actions = ["calculate_metrics_action"]

    def calculate_metrics_action(self, request, queryset):
        """
        Acción para recalcular métricas de sesiones.
        """
        count = 0
        for session in queryset:
            session.calculate_metrics()
            count += 1

        self.message_user(request, f"Métricas recalculadas para {count} sesiones")

    calculate_metrics_action.short_description = "Recalcular métricas de sesiones"
