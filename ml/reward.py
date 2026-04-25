"""
Módulo de Función de Recompensa (Reward Function) para el Agente RL.

Calcula el reward basándose en:
- Feedback del usuario (skip: -1, completed: +1)
- Contexto externo (clima, noticias)
- Características de audio del track
- Historico del usuario
"""

import numpy as np


class RewardCalculator:
    """
    Calcula el reward (recompensa) para entrenar el agente de RL.

    El reward es una señal que guía al agente a seleccionar tracks óptimos
    basándose en el contexto actual y el feedback del usuario.
    """

    def __init__(
        self,
        base_reward: float = 1.0,
        skip_penalty: float = -1.0,
        completion_bonus: float = 1.0,
        context_weight: float = 0.2,
        audio_feature_weight: float = 0.15,
    ):
        """
        Inicializa la función de recompensa.

        Args:
            base_reward: Recompensa base neutral
            skip_penalty: Penalización por skip del usuario
            completion_bonus: Bonificación por completar la canción
            context_weight: Peso del contexto en el reward
            audio_feature_weight: Peso de las características de audio
        """
        self.base_reward = base_reward
        self.skip_penalty = skip_penalty
        self.completion_bonus = completion_bonus
        self.context_weight = context_weight
        self.audio_feature_weight = audio_feature_weight

    def calculate_reward(
        self,
        user_feedback: str | None = None,
        weather_context: dict | None = None,
        track_audio_features: dict | None = None,
        user_history: dict | None = None,
    ) -> float:
        """
        Calcula el reward total basándose en múltiples factores.

        Args:
            user_feedback: Feedback del usuario ('skip', 'completed', None)
            weather_context: Diccionario con datos del clima
            track_audio_features: Diccionario con características de audio del track
            user_history: Diccionario con el historico del usuario

        Returns:
            float: Valor de recompensa entre -1.0 y 2.0+

        Examples:
            >>> calculator = RewardCalculator()
            >>> # Completar una canción en clima favorable
            >>> r = calculator.calculate_reward(
            ...     user_feedback='completed',
            ...     weather_context={'temperature': 22, 'mood': 'clear'},
            ...     track_audio_features={'energy': 0.8, 'danceability': 0.7},
            ...     user_history={'avg_skip_rate': 0.3}
            ... )
            >>> assert r > 1.0
        """
        reward = self.base_reward

        # 1. Feedback del usuario (factor dominante)
        feedback_reward = self._calculate_feedback_reward(user_feedback)
        reward += feedback_reward

        # 2. Contexto externo (clima, noticias)
        if weather_context:
            context_reward = self._calculate_context_reward(weather_context)
            reward += context_reward * self.context_weight

        # 3. Características de audio
        if track_audio_features:
            audio_reward = self._calculate_audio_feature_reward(track_audio_features)
            reward += audio_reward * self.audio_feature_weight

        # 4. Consistencia con historico del usuario
        if user_history:
            consistency_reward = self._calculate_consistency_reward(
                track_audio_features, user_history
            )
            reward += consistency_reward * 0.1

        return reward

    def _calculate_feedback_reward(self, user_feedback: str | None) -> float:
        """
        Calcula la recompensa basada en el feedback del usuario.

        - skip: penalización fuerte
        - completed: bonificación
        - None/no_action: neutral
        """
        if user_feedback == "skip":
            return self.skip_penalty
        elif user_feedback == "completed":
            return self.completion_bonus
        elif user_feedback == "skip_immediate":
            # Skip muy rápido (primeros segundos)
            return self.skip_penalty * 1.5
        else:
            return 0.0

    def _calculate_context_reward(self, weather_context: dict) -> float:
        """
        Calcula bonificación basada en el contexto del clima.

        La idea es que ciertos tipos de música van mejor con cierto clima.
        Por ejemplo:
        - Música energética (danceability alta) → clima soleado, energético
        - Música tranquila (valence baja) → clima nublado, lluvioso
        """
        reward = 0.0

        # Bonus si el clima es agradable (temperatura moderada)
        temperature = weather_context.get("temperature", 20)
        if 18 <= temperature <= 28:
            reward += 0.3
        elif temperature < 0 or temperature > 35:
            reward -= 0.2

        # Bonus si el clima es despejado (motivación)
        main_status = weather_context.get("main_status", "").lower()
        if main_status in ["clear", "sunny", "clouds"]:
            reward += 0.2
        elif main_status in ["rain", "thunderstorm"]:
            reward -= 0.1

        # Humedad (demasiada humedad es incómoda)
        humidity = weather_context.get("humidity", 50)
        if 30 <= humidity <= 70:
            reward += 0.1
        elif humidity > 85:
            reward -= 0.15

        return reward

    def _calculate_audio_feature_reward(self, audio_features: dict) -> float:
        """
        Calcula bonificación basada en las características de audio del track.

        Favorece tracks con features balanceadas (ni demasiado extremos).
        """
        reward = 0.0

        # Balancean energía y danceability (buena combinación)
        energy = audio_features.get("energy", 0.5)
        danceability = audio_features.get("danceability", 0.5)

        # Energía moderada es mejor
        if 0.4 <= energy <= 0.8:
            reward += 0.2
        elif energy < 0.2 or energy > 0.95:
            reward -= 0.1

        # Danceability moderada a alta es generalmente atractiva
        if danceability > 0.6:
            reward += 0.15

        # Valence (positividad) es importante
        valence = audio_features.get("valence", 0.5)
        if 0.4 <= valence <= 0.8:
            reward += 0.1

        # Evitar tracks demasiado acústicos o instrumentales
        acousticness = audio_features.get("acousticness", 0.3)
        instrumentalness = audio_features.get("instrumentalness", 0.0)

        if acousticness > 0.9:
            reward -= 0.05
        if instrumentalness > 0.8:
            reward -= 0.05

        return reward

    def _calculate_consistency_reward(
        self,
        current_audio_features: dict | None,
        user_history: dict,
    ) -> float:
        """
        Calcula bonificación basada en la consistencia con preferencias del usuario.

        Si el usuario típicamente le gustan tracks con ciertas características,
        un track similar debería recibir reward positivo.
        """
        if not current_audio_features or not user_history:
            return 0.0

        reward = 0.0

        # Comparar con preferencias históricas
        avg_energy = user_history.get("avg_energy", 0.5)
        avg_danceability = user_history.get("avg_danceability", 0.5)
        avg_valence = user_history.get("avg_valence", 0.5)

        current_energy = current_audio_features.get("energy", 0.5)
        current_danceability = current_audio_features.get("danceability", 0.5)
        current_valence = current_audio_features.get("valence", 0.5)

        # Similitud en features (cercania = bonus)
        energy_diff = abs(current_energy - avg_energy)
        if energy_diff < 0.2:
            reward += 0.15
        elif energy_diff < 0.4:
            reward += 0.05

        danceability_diff = abs(current_danceability - avg_danceability)
        if danceability_diff < 0.2:
            reward += 0.15
        elif danceability_diff < 0.4:
            reward += 0.05

        valence_diff = abs(current_valence - avg_valence)
        if valence_diff < 0.2:
            reward += 0.1

        # Skip rate del usuario (si hace muchos skips, es más exigente)
        skip_rate = user_history.get("skip_rate", 0.30)
        if skip_rate > 0.5:
            # Usuario muy exigente: recompensa más conservadora
            reward *= 0.8

        return reward

    def normalize_reward(
        self, reward: float, min_val: float = -2.0, max_val: float = 2.0
    ) -> float:
        """
        Normaliza el reward a un rango específico usando clipping.

        Args:
            reward: Valor bruto de recompensa
            min_val: Valor mínimo del rango
            max_val: Valor máximo del rango

        Returns:
            float: Reward normalizado en el rango [min_val, max_val]
        """
        return np.clip(reward, min_val, max_val)


# Instancia singleton para usar en toda la aplicación
_reward_calculator_instance = None


def get_reward_calculator(**kwargs) -> RewardCalculator:
    """
    Obtiene o crea la instancia global de RewardCalculator.

    Args:
        **kwargs: Parámetros para inicializar RewardCalculator

    Returns:
        RewardCalculator: Instancia global
    """
    global _reward_calculator_instance
    if _reward_calculator_instance is None:
        _reward_calculator_instance = RewardCalculator(**kwargs)
    return _reward_calculator_instance
