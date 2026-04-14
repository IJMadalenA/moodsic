"""
Módulo State Builder para Reinforcement Learning.

Construye vectores de estado (observations) que representa el contexto actual
incluyendo: clima, noticias, características de audio, historico del usuario.

La salida es un vector normalizado que se usa como entrada al agente RL.
"""

from typing import Dict, List, Optional, Tuple

import numpy as np
from django.contrib.auth import get_user_model
from django.db.models import Avg, Q
from django.utils import timezone

User = get_user_model()


class StateBuilder:
    """
    Construye vectores de estado normalizados para el agente RL.
    
    Un estado representa toda la información relevante en un momento dado:
    - Contexto del clima
    - Noticias recientes
    - Historico del usuario
    - Características de audio del track anterior
    
    El vector de estado es normalizado a [0, 1] para mejor convergencia del RL.
    """

    def __init__(
        self,
        state_dim: int = 45,
        weather_features: int = 10,
        audio_features_dim: int = 12,
        user_history_dim: int = 8,
        context_embedding_dim: int = 15,
    ):
        """
        Inicializa el State Builder.
        
        Args:
            state_dim: Dimensión total del vector de estado
            weather_features: Número de features de clima
            audio_features_dim: Número de características de audio
            user_history_dim: Número de features de historico
            context_embedding_dim: Número de features de contexto general
        """
        self.state_dim = state_dim
        self.weather_features = weather_features
        self.audio_features_dim = audio_features_dim
        self.user_history_dim = user_history_dim
        self.context_embedding_dim = context_embedding_dim

        # Normalizadores (min-max scaling)
        self.normalizers = {
            "temperature": {"min_val": -50, "max_val": 50},  # °C
            "humidity": {"min_val": 0, "max_val": 100},  # %
            "wind_speed": {"min_val": 0, "max_val": 30},  # m/s
            "pressure": {"min_val": 900, "max_val": 1100},  # hPa
            "visibility": {"min_val": 0, "max_val": 100000},  # metros
            "audio_feature": {"min_val": 0, "max_val": 1},  # Spotify features [0, 1]
            "energy": {"min_val": 0, "max_val": 1},
            "danceability": {"min_val": 0, "max_val": 1},
        }

    def build_state(
        self,
        user: "User",
        weather_context: Optional[Dict] = None,
        current_track: Optional[Dict] = None,
        time_of_day: Optional[str] = None,
        news_contexts: Optional[List[Dict]] = None,
    ) -> np.ndarray:
        """
        Construye el vector de estado completo.
        
        Args:
            user: Usuario para el que se construye el estado
            weather_context: Diccionario con datos del clima
            current_track: Diccionario con características del track actual
            time_of_day: 'morning', 'afternoon', 'evening', 'night'
            
        Returns:
            np.ndarray: Vector de estado normalizado de shape (state_dim,)
            
        Example:
            >>> builder = StateBuilder()
            >>> weather = {'temperature': 22, 'humidity': 60, 'wind_speed': 5}
            >>> track = {'energy': 0.8, 'danceability': 0.7}
            >>> state = builder.build_state(user, weather, track)
            >>> assert state.shape == (45,)
            >>> assert np.all((state >= 0) & (state <= 1))
        """
        state_components = []

        # 1. Features de clima (10 features)
        weather_vec = self._extract_weather_features(weather_context)
        state_components.append(weather_vec)

        # 2. Features de audio del track actual (12 features)
        audio_vec = self._extract_audio_features(current_track)
        state_components.append(audio_vec)

        # 3. Características del usuario basadas en historico (8 features)
        user_vec = self._extract_user_history_features(user)
        state_components.append(user_vec)

        # 4. Features de contexto temporal (15 features: hora, día, estación)
        context_vec = self._extract_context_features(time_of_day, news_contexts)
        state_components.append(context_vec)

        # Concatenar todos los componentes
        state = np.concatenate(state_components, axis=0)

        # Asegurar que el tamaño es correcto
        if len(state) < self.state_dim:
            # Padding con ceros si es necesario
            state = np.pad(state, (0, self.state_dim - len(state)))
        elif len(state) > self.state_dim:
            # Truncar si es más grande
            state = state[: self.state_dim]

        return state.astype(np.float32)

    def _extract_weather_features(self, weather_context: Optional[Dict]) -> np.ndarray:
        """
        Extrae features normalizadas del contexto climático.
        
        Returns un vector de 10 features:
        [temp, feels_like, humidity, wind_speed, pressure, visibility, 
         clouds, rain_prob, is_raining, is_snowing]
        """
        features = []

        if weather_context is None:
            weather_context = {}

        # Temperatura normalizada
        temp = weather_context.get("temperature", 20)
        norm_temp = self._normalize(temp, self.normalizers["temperature"])
        features.append(norm_temp)

        # Sensación térmica
        feels_like = weather_context.get("feels_like", temp)
        norm_feels_like = self._normalize(feels_like, self.normalizers["temperature"])
        features.append(norm_feels_like)

        # Humedad
        humidity = weather_context.get("humidity", 60)
        norm_humidity = self._normalize(humidity, self.normalizers["humidity"])
        features.append(norm_humidity)

        # Velocidad del viento
        wind_speed = weather_context.get("wind_speed", 0)
        norm_wind = self._normalize(wind_speed, self.normalizers["wind_speed"])
        features.append(norm_wind)

        # Presión
        pressure = weather_context.get("pressure", 1013)
        norm_pressure = self._normalize(pressure, self.normalizers["pressure"])
        features.append(norm_pressure)

        # Visibilidad
        visibility = weather_context.get("visibility", 10000)
        norm_visibility = self._normalize(
            visibility, self.normalizers["visibility"]
        )
        features.append(norm_visibility)

        # Nubosidad
        clouds = weather_context.get("clouds_all", 50)
        norm_clouds = self._normalize(clouds, {"min_val": 0, "max_val": 100})
        features.append(norm_clouds)

        # Probabilidad de lluvia (estimada)
        rain_prob = weather_context.get("rain_probability", 0)
        features.append(float(rain_prob) / 100.0)

        # Indicador: ¿está lloviendo?
        is_raining = float(
            weather_context.get("main_status", "").lower() in ["rain", "drizzle"]
        )
        features.append(is_raining)

        # Indicador: ¿está nevando?
        is_snowing = float(weather_context.get("main_status", "").lower() == "snow")
        features.append(is_snowing)

        return np.array(features[:self.weather_features], dtype=np.float32)

    def _extract_audio_features(self, current_track: Optional[Dict]) -> np.ndarray:
        """
        Extrae features de audio normalizadas del track actual.
        
        Returns un vector de 12 features:
        [energy, danceability, valence, acousticness, instrumentalness,
         liveness, loudness, tempo, speechiness, key, mode, time_signature]
        """
        features = []

        if current_track is None:
            current_track = {}

        # Spotify audio features (todos están en [0, 1] o rango específico)
        audio_feature_names = [
            "energy",
            "danceability",
            "valence",
            "acousticness",
            "instrumentalness",
            "liveness",
        ]

        for feat_name in audio_feature_names:
            value = current_track.get(feat_name, 0.5)
            # Normalizar a [0, 1]
            norm_value = np.clip(float(value), 0.0, 1.0)
            features.append(norm_value)

        # Loudness (típicamente [-60, 0] dB)
        loudness = current_track.get("loudness", -5)
        norm_loudness = self._normalize(loudness, {"min_val": -60, "max_val": 0})
        features.append(norm_loudness)

        # Tempo (típicamente [60, 200] BPM)
        tempo = current_track.get("tempo", 120)
        norm_tempo = self._normalize(tempo, {"min_val": 60, "max_val": 200})
        features.append(norm_tempo)

        # Speechiness (voz/palabras)
        speechiness = current_track.get("speechiness", 0.0)
        features.append(np.clip(float(speechiness), 0.0, 1.0))

        # Key (0-11, normalizado a [0, 1])
        key = current_track.get("key", 0)
        norm_key = float(key) / 11.0 if key >= 0 else 0.0
        features.append(np.clip(norm_key, 0.0, 1.0))

        # Mode (0=minor, 1=major) - ya está normalizado
        mode = float(current_track.get("mode", 0))
        features.append(np.clip(mode, 0.0, 1.0))

        # Time signature (3, 4, 5, etc.) - normalizar a [0, 1]
        time_sig = current_track.get("time_signature", 4)
        norm_time_sig = float(time_sig) / 7.0
        features.append(np.clip(norm_time_sig, 0.0, 1.0))

        return np.array(features[:self.audio_features_dim], dtype=np.float32)

    def _extract_user_history_features(self, user: "User") -> np.ndarray:
        """
        Extrae features de historico del usuario.
        
        Returns un vector de 8 features relacionadas al comportamiento del usuario.
        """
        features = []

        try:
            from apps.music.models import Track
            from apps.interactions.models import Interaction  # cuando exista

            # Skip rate (proporción de tracks que skipped)
            # Esto requeriría un modelo Interaction que aún no existe
            skip_rate = 0.3  # Default
            features.append(skip_rate)

            # Completion rate
            completion_rate = 0.7  # Default
            features.append(completion_rate)

        except Exception:
            # Si los modelos no existen todavía, usar defaults
            features.extend([0.3, 0.7])

        # Features adicionales del usuario
        features.extend([
            0.5,  # Energy preference (default neutral)
            0.6,  # Danceability preference
            0.5,  # Valence preference
            0.4,  # Acousticness preference
            0.2,  # Instrumentalness preference (prefer más vocals)
            float(user.is_spotify_connected),  # ¿Está conectado a Spotify?
            0.5,  # Engagement score (default neutral)
            0.6,  # Diversity preference (cuánto varía su gusto)
        ])

        return np.array(features[:self.user_history_dim], dtype=np.float32)

    def _extract_context_features(
        self,
        time_of_day: Optional[str],
        news_contexts: Optional[List[Dict]] = None,
    ) -> np.ndarray:
        """
        Extrae features contextuales: hora del día, día de la semana, temporada.
        
        Returns un vector de 15 features.
        """
        features = []

        # Hora del día (one-hot encoding: morning, afternoon, evening, night)
        hour_encoding = self._encode_time_of_day(time_of_day)
        features.extend(hour_encoding)

        # Día de la semana
        now = timezone.now()
        day_of_week = now.weekday()  # 0=Lunes, 6=Domingo
        is_weekend = float(day_of_week >= 5)
        norm_day = float(day_of_week) / 6.0

        features.append(is_weekend)
        features.append(norm_day)

        # Mes/Estación (aproximado)
        month = now.month
        season = self._get_season(month)
        season_encoding = self._encode_season(season)
        features.extend(season_encoding)

        # Hora del día (como número 0-23, normalizado)
        hour = now.hour
        norm_hour = float(hour) / 23.0
        features.append(norm_hour)

        # Minuto del día (para granularity)
        minute = now.minute
        norm_minute = float(minute) / 59.0
        features.append(norm_minute)

        # Features temporales adicionales
        day_of_month = now.day
        norm_day_of_month = float(day_of_month) / 31.0
        features.append(norm_day_of_month)

        # Es festivo/fin de semana
        features.append(is_weekend)

        # Agregar señales de noticias en vivo (sentimiento, breaking, volumen)
        news_vec = self._extract_news_features(news_contexts)
        features.extend(news_vec)

        # Hora de pico esperada
        is_peak_hour = float(hour in [8, 9, 17, 18, 19])  # Horas común de peak
        features.append(is_peak_hour)

        return np.array(features[:self.context_embedding_dim], dtype=np.float32)

    @staticmethod
    def _extract_news_features(news_contexts: Optional[List[Dict]]) -> List[float]:
        """Return compact news-derived features for the context embedding."""
        if not news_contexts:
            return [0.5, 0.0, 0.0]

        sentiment_values = [
            float(item.get("sentiment_score", 0.0))
            for item in news_contexts
        ]
        avg_sentiment = sum(sentiment_values) / len(sentiment_values)
        # Map [-1, 1] sentiment into [0, 1]
        norm_sentiment = max(0.0, min(1.0, (avg_sentiment + 1.0) / 2.0))

        breaking_ratio = sum(
            1 for item in news_contexts if item.get("is_breaking")
        ) / float(len(news_contexts))

        norm_news_volume = min(1.0, len(news_contexts) / 20.0)
        return [norm_sentiment, breaking_ratio, norm_news_volume]

    @staticmethod
    def _normalize(value: float, range_dict: Dict) -> float:
        """
        Normaliza un valor al rango [0, 1] usando min-max scaling.
        
        Args:
            value: Valor a normalizar
            range_dict: Dict con 'min_val' y 'max_val'
            
        Returns:
            float: Valor normalizado en [0, 1]
        """
        min_val = range_dict.get("min_val", 0)
        max_val = range_dict.get("max_val", 1)

        if max_val == min_val:
            return 0.0

        norm = (float(value) - min_val) / (max_val - min_val)
        return np.clip(norm, 0.0, 1.0)

    @staticmethod
    def _encode_time_of_day(time_of_day: Optional[str]) -> List[float]:
        """
        One-hot encoding de la hora del día.
        
        Returns: [is_morning, is_afternoon, is_evening, is_night]
        """
        encoding = [0.0, 0.0, 0.0, 0.0]

        if time_of_day == "morning":
            encoding[0] = 1.0
        elif time_of_day == "afternoon":
            encoding[1] = 1.0
        elif time_of_day == "evening":
            encoding[2] = 1.0
        elif time_of_day == "night":
            encoding[3] = 1.0
        else:
            # Inferir de la hora actual
            now = timezone.now()
            hour = now.hour
            if 6 <= hour < 12:
                encoding[0] = 1.0
            elif 12 <= hour < 18:
                encoding[1] = 1.0
            elif 18 <= hour <= 23:
                encoding[2] = 1.0
            else:
                encoding[3] = 1.0

        return encoding

    @staticmethod
    def _get_season(month: int) -> str:
        """Retorna la estación del año basada en el mes."""
        if month in [12, 1, 2]:
            return "winter"
        elif month in [3, 4, 5]:
            return "spring"
        elif month in [6, 7, 8]:
            return "summer"
        else:
            return "autumn"

    @staticmethod
    def _encode_season(season: str) -> List[float]:
        """
        One-hot encoding de la estación.
        
        Returns: [is_winter, is_spring, is_summer, is_autumn]
        """
        seasons = ["winter", "spring", "summer", "autumn"]
        encoding = [0.0, 0.0, 0.0, 0.0]

        if season in seasons:
            encoding[seasons.index(season)] = 1.0

        return encoding


# Instancia global
_state_builder_instance = None


def get_state_builder(**kwargs) -> StateBuilder:
    """
    Obtiene o crea la instancia global de StateBuilder.
    """
    global _state_builder_instance
    if _state_builder_instance is None:
        _state_builder_instance = StateBuilder(**kwargs)
    return _state_builder_instance
