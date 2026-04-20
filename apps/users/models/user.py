from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """
    Modelo de Usuario personalizado para Moodsic.
    
    Heredamos de AbstractUser para mantener las funcionalidades estándar de Django 
    (password hashing, permisos, etc.) pero extendemos el modelo para almacenar 
    la vinculación con la API de Spotify y los tokens de sesión.
    """

    # Identificador único de Spotify (ej. 'spotify:user:123456789')
    # Se usa para vincular nuestra base de datos con los recursos del usuario en Spotify.
    spotify_id = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        unique=True,
        help_text="ID único proporcionado por la API de Spotify"
    )

    # URL de la imagen de perfil del usuario en Spotify
    avatar_url = models.URLField(
        max_length=500, 
        blank=True, 
        default="",
        help_text="URL de la imagen de perfil de Spotify"
    )

    # Flag booleano para comprobaciones rápidas de estado de conexión en el frontend
    is_spotify_connected = models.BooleanField(
        default=False,
        help_text="Indica si el usuario ha completado el flujo de OAuth exitosamente"
    )

    # --- CAMPOS DE TOKEN OAUTH ---
    # Estos campos permiten que el backend realice peticiones sin intervención del usuario.
    
    # El Access Token es volátil (dura 1 hora). Se guarda como TextField por seguridad en longitud.
    access_token = models.TextField(
        blank=True, 
        null=True,
        help_text="Token de acceso para llamadas a la API"
    )

    # El Refresh Token permite obtener un nuevo access_token cuando el anterior expira.
    # Es fundamental para que el agente de ML trabaje en segundo plano (asíncrono).
    refresh_token = models.TextField(
        blank=True, 
        null=True,
        help_text="Token para refrescar la sesión sin pedir login al usuario"
    )

    # Almacenamos la fecha de expiración para validar si el token es vigente 
    # antes de intentar realizar una llamada a la API.
    token_expires_at = models.DateTimeField(
        blank=True, 
        null=True,
        help_text="Momento exacto en el que el access_token deja de ser válido"
    )

    class Meta:
        # Personalizamos el nombre de la tabla para seguir la estructura definida en la fase 1
        db_table = "auth_user_custom"
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        """Retorna el email o el username como representación del objeto"""
        return self.email if self.email else self.username
