"""
Modelo Interaction: registra la interacción del usuario con los tracks.

Almacena feedback (skip, completed), rewards, y métricas para entrenar el agente RL.
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.music.models import Track


class Interaction(models.Model):
    """
    Registra la interacción de un usuario con una canción.

    Incluye el tipo de feedback (skip, completed, etc) y la recompensa calculada.
    Esto es crucial para entrenar el agente RL.
    """

    FEEDBACK_CHOICES = [
        ("completed", _("Canción completada")),
        ("skip", _("Salto normal")),
        ("skip_immediate", _("Salto inmediato (< 5 seg)")),
        ("replay", _("Reproducida de nuevo")),
        ("added_to_playlist", _("Añadida a playlist")),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="interactions",
        verbose_name=_("Usuario"),
    )
    track = models.ForeignKey(
        Track,
        on_delete=models.CASCADE,
        related_name="interactions",
        verbose_name=_("Canción"),
    )

    # Feedback del usuario
    feedback = models.CharField(
        max_length=20,
        choices=FEEDBACK_CHOICES,
        default="completed",
        verbose_name=_("Tipo de feedback"),
    )

    # Contexto en el que ocurrió la interacción
    weather_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("ID Contexto climático"),
    )
    news_ids = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("IDs de noticias"),
    )

    # Métricas de la interacción
    reward = models.FloatField(
        default=0.0,
        verbose_name=_("Recompensa calculada"),
    )
    play_duration = models.IntegerField(
        default=0,
        verbose_name=_("Duración reproducida (segundos)"),
        help_text="Cuántos segundos del track se reprodujeron",
    )
    track_duration = models.IntegerField(
        default=0,
        verbose_name=_("Duración total del track (segundos)"),
    )

    # Completeness: qué porcentaje del track se escuchó
    completion_percentage = models.FloatField(
        default=0.0,
        verbose_name=_("Porcentaje completado (%)"),
    )

    # Metadatos
    session_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name=_("ID de sesión"),
        help_text="Para agrupar interacciones de una sesión",
    )
    playlist_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name=_("ID de playlist (Spotify)"),
    )

    # Tiempo
    started_at = models.DateTimeField(
        verbose_name=_("Hora de inicio"),
        auto_now_add=True,
    )
    ended_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Hora de término"),
    )

    # Atributos calculados
    is_positive = models.BooleanField(
        default=True,
        verbose_name=_("¿Es feedback positivo?"),
        help_text="True si feedback != 'skip'",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Interacción")
        verbose_name_plural = _("Interacciones")
        ordering = ("-started_at",)
        indexes = [
            models.Index(fields=["user", "-started_at"]),
            models.Index(fields=["track", "-started_at"]),
            models.Index(fields=["feedback"]),
            models.Index(fields=["session_id"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.track.name} ({self.feedback})"

    def save(self, *args, **kwargs):
        """
        Calcula campos derivados antes de guardar.
        """
        # Calcular porcentaje de completitud
        if self.track_duration > 0:
            self.completion_percentage = (
                self.play_duration / self.track_duration
            ) * 100

        # Clasificar feedback como positivo o negativo
        self.is_positive = not self.feedback.startswith("skip")

        super().save(*args, **kwargs)


class InteractionSession(models.Model):
    """
    Agrupa interacciones en sesiones de usuario.

    Una sesión representa un período de uso continuo.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="interaction_sessions",
        verbose_name=_("Usuario"),
    )

    session_id = models.CharField(
        max_length=255,
        unique=True,
        verbose_name=_("ID de sesión"),
    )

    # Contexto de la sesión
    weather_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("ID Contexto al inicio de sesión"),
    )

    # Métricas agregadas
    total_tracks = models.IntegerField(
        default=0,
        verbose_name=_("Total de canciones reproducidas"),
    )
    skip_count = models.IntegerField(
        default=0,
        verbose_name=_("Total de skips"),
    )
    completed_count = models.IntegerField(
        default=0,
        verbose_name=_("Total de canciones completadas"),
    )
    average_reward = models.FloatField(
        default=0.0,
        verbose_name=_("Reward promedio de la sesión"),
    )
    total_reward = models.FloatField(
        default=0.0,
        verbose_name=_("Reward total de la sesión"),
    )

    # Duración
    started_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Inicio de sesión"),
    )
    ended_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Fin de sesión"),
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name=_("¿Sesión activa?"),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Sesión de interacción")
        verbose_name_plural = _("Sesiones de interacción")
        ordering = ("-started_at",)
        indexes = [
            models.Index(fields=["user", "-started_at"]),
            models.Index(fields=["session_id"]),
        ]

    def __str__(self):
        return f"{self.user.username} - Session {self.session_id[:8]}"

    def calculate_metrics(self):
        """
        Calcula las métricas agregadas de la sesión según las interacciones.
        """
        from django.db.models import Avg

        interactions = Interaction.objects.filter(session_id=self.session_id)

        self.total_tracks = interactions.count()
        self.skip_count = interactions.filter(feedback__startswith="skip").count()
        self.completed_count = interactions.filter(feedback="completed").count()
        self.average_reward = interactions.aggregate(avg=Avg("reward"))["avg"] or 0.0
        self.total_reward = sum(interactions.values_list("reward", flat=True))

        self.save()
