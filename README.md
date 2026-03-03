# moodsic
Generador de Playlists Inteligentes en Spotify Basado en Contextos Externos.

MoodSic es un sistema innovador que crea playlists personalizadas en Spotify adaptadas a tu entorno real. Usando Aprendizaje por Refuerzo (Reinforcement Learning) y técnicas de Big Data, el agente IA aprende de tu feedback (skips o listens) para proponer tracks perfectos, mejorando la relevancia y el engagement.

Características clave:

- Integración en tiempo real con APIs como OpenWeather, NewsAPI y Fitbit.
- Modelo RL para recomendaciones dinámicas.
- Prototipo en Python con Spotipy y TensorFlow.
- Evaluado con métricas de reward y pruebas con usuarios.

moodsic/
│
├── manage.py
├── requirements.txt
├── help.txt
├── README.md
├── .env
├── .gitignore
│
├── config/                         # Configuración global de Django
│   ├── __init__.py
│   ├── settings.py                  # Configuración principal (DB, apps, middleware)
│   ├── urls.py                      # Router principal del proyecto
│   ├── asgi.py
│   └── wsgi.py
│
├── apps/                            # Lógica funcional del sistema
│   │
│   ├── users/                        # Autenticación OAuth Spotify
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py                  # UserProfile (tokens, spotify_id)
│   │   ├── views.py                    # Endpoints login/callback
│   │   ├── urls.py
│   │   ├── tests.py
│   │   └── services/
│   │       ├── __init__.py
│   │       └── spotify_auth_service.py # Lógica OAuth
│   │
│   ├── music/                         # Gestión de canciones y audio features
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py                   # Track, audio features
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── tests.py
│   │   └── services/
│   │       ├── __init__.py
│   │       └── spotify_music_service.py
│   │
│   ├── context/                        # Clima + Noticias (contexto externo)
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py                    # WeatherContext, NewsContext
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── tests.py
│   │   ├── schemas.py                   # Esquemas API (Django-Ninja)
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── weather_service.py        # OpenWeather API
│   │       └── news_service.py           # NewsAPI
│   │
│   ├── interactions/                     # Feedback y recompensa
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py                     # Interaction (skips, reward)
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── tests.py
│   │   └── services/
│   │       ├── __init__.py
│   │       └── reward_service.py          # Cálculo de reward
│   │
│   └── dashboard/                        # Métricas y visualización
│       ├── __init__.py
│       ├── views.py                       # Métricas: reward medio, skips
│       ├── urls.py
│       └── tests.py
│
├── ml/                                   # Inteligencia Artificial (Reinforcement Learning)
│   ├── __init__.py
│   ├── agent.py                           # Agente RL
│   ├── state_builder.py                    # Construcción vector estado
│   ├── reward.py                           # Función matemática reward
│   └── training.py                         # Entrenamiento modelo
│
├── pipelines/                             # ETL y procesamiento datos
│   ├── __init__.py
│   ├── etl_weather.py                      # Datos clima → BD
│   ├── etl_news.py                         # Datos noticias → BD
│   └── state_pipeline.py                    # Construcción estado RL
│
└── docker/                                # Infraestructura
    ├── Dockerfile
    └── docker-compose.yml                  # PostgreSQL + (Redis opcional)