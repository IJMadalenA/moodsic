# Infraestructura y Autenticación - Moodsic

Este documento describe la arquitectura de infraestructura básica del proyecto y el flujo de autenticación, con especial atención a la integración con Spotify.

## 1. Infraestructura Base

- **Lenguaje**: Python 3.12+
- **Framework Web**: [Django 6.0+](https://www.djangoproject.com/)
- **Gestión de Dependencias**: [uv](https://github.com/astral-sh/uv) (Reemplaza a pip/poetry/pipenv).
- **Base de Datos**:
  - Local: SQLite (`db.sqlite3`).
  - Producción: PostgreSQL (vía `psycopg`).
- **Variables de Entorno**: Gestionadas mediante `django-environ`. Se deben definir en un archivo `.env` en la raíz del proyecto.

### Comandos de Infraestructura
- **Sincronizar entorno**: `uv sync`
- **Ejecutar migraciones**: `uv run manage.py migrate`
- **Levantar servidor**: `uv run manage.py runserver`

## 2. Sistema de Autenticación

Moodsic utiliza un modelo de usuario personalizado y se integra con `django-allauth` para el inicio de sesión social.

### Modelo de Usuario (`CustomUser`)
Ubicado en `apps/users/models/user.py`, el modelo `User` hereda de `AbstractUser` para mantener la funcionalidad estándar de Django mientras permite campos adicionales:
- `spotify_id`: Identificador único del usuario en Spotify (`CharField`).
- `avatar_url`: URL de la imagen de perfil obtenida de Spotify (`URLField`).
- `is_spotify_connected`: Flag de estado de la conexión (`BooleanField`).

### Spotify Social Login
La integración se realiza mediante `django-allauth`:
- **Proveedor**: Spotify.
- **Adapter Personalizado**: `MoodsicSocialAccountAdapter` (`apps/users/adapter.py`). Sobrescribe `save_user` para capturar automáticamente el ID y el avatar de Spotify al registrarse.
- **Scopes (Permisos)**: Se solicitan permisos para leer el perfil, el email y gestionar playlists (definidos en `SOCIALACCOUNT_PROVIDERS` en `settings.py`).

## 3. Gestión de Tokens de Spotify

La persistencia y el refresco de los tokens son críticos para la automatización de playlists sin intervención del usuario.

### `SpotifyMusicService`
Servicio central (`apps/music/services/spotify_music_service.py`) que actúa como puente entre Django y la librería `spotipy`.

**Características principales:**
- **Persistencia**: Recupera el `SocialToken` asociado al usuario.
- **Refresco Automático**: Compara `expires_at` con el tiempo actual. Si el token ha expirado, utiliza el `refresh_token` para obtener uno nuevo y lo persiste de forma transparente.
- **Instanciación**: Al inicializar el servicio con un usuario, devuelve un cliente `spotipy.Spotify` listo para usar.

## 4. Comandos de Verificación

Para facilitar el diagnóstico de la integración, se incluye un comando de gestión personalizado.

### Verificación de Spotify
Verifica la presencia de credenciales en el entorno y la conectividad real con la API de Spotify (usando *Client Credentials Flow*).

```bash
uv run manage.py verify_spotify
```

**Resultados esperados:**
- Confirmación de variables `SPOTIPY_CLIENT_ID`, `SPOTIPY_CLIENT_SECRET` y `SPOTIPY_REDIRECT_URI`.
- Prueba de conexión exitosa con la API mediante una búsqueda de prueba.
