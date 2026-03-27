"""
Agente de Reinforcement Learning para generación de playlists.

Utiliza Deep Q-Network (DQN) para aprender a seleccionar tracks óptimos
basándose en el contexto (clima, noticias) y feedback del usuario.

Arquitectura:
- Q-Network: Red neuronal que predice Q-values para cada acción (track)
- Memory Buffer: Almacena experiencias para entrenamiento
- Epsilon-Greedy: Exploración vs. Explotación
"""

import logging
from collections import deque
from typing import Dict, List, Optional, Tuple

import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers

logger = logging.getLogger(__name__)


class DQNAgent:
    """
    Deep Q-Network Agent para selección de canciones.
    
    El agente aprende a mapear estados (contexto) a acciones (tracks)
    que maximicen el reward esperado (satisfacción del usuario).
    """

    def __init__(
        self,
        state_dim: int = 45,
        action_dim: int = 100,
        learning_rate: float = 0.001,
        gamma: float = 0.99,
        epsilon: float = 1.0,
        epsilon_decay: float = 0.995,
        epsilon_min: float = 0.01,
        memory_size: int = 10000,
        batch_size: int = 64,
        hidden_dim: int = 128,
        model_path: Optional[str] = None,
    ):
        """
        Inicializa el Agente DQN.
        
        Args:
            state_dim: Dimensión del vector de estado (45)
            action_dim: Número de acciones posibles (tracks disponibles)
            learning_rate: Tasa de aprendizaje
            gamma: Factor de descuento para reward futuro
            epsilon: Probabilidad de exploración inicial
            epsilon_decay: Factor de decaimiento de epsilon
            epsilon_min: Epsilon mínimo
            memory_size: Tamaño del replay buffer
            batch_size: Tamaño del batch para entrenamiento
            hidden_dim: Dimensión de capas ocultas
            model_path: Ruta para guardar/cargar el modelo
        """
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.learning_rate = learning_rate
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.epsilon_min = epsilon_min
        self.memory_size = memory_size
        self.batch_size = batch_size
        self.hidden_dim = hidden_dim
        self.model_path = model_path or "ml/models/dqn_model.h5"

        # Replay buffer (memoria de experiencias)
        self.memory = deque(maxlen=memory_size)

        # Redes neuronales
        self.q_network = self._build_network()
        self.target_network = self._build_network()
        self._update_target_network()

        # Optimizador
        self.optimizer = keras.optimizers.Adam(learning_rate=learning_rate)

        # Counters
        self.steps = 0
        self.episodes = 0

        logger.info(f"DQN Agent inicializado. State dim: {state_dim}, Action dim: {action_dim}")

    def _build_network(self) -> keras.Model:
        """
        Construye la red neuronal Q-Network.
        
        Arquitectura: Input -> Dense(128) -> ReLU -> Dense(128) -> ReLU -> Output
        """
        inputs = layers.Input(shape=(self.state_dim,))

        # Primera capa oculta
        x = layers.Dense(self.hidden_dim, activation="relu")(inputs)
        x = layers.BatchNormalization()(x)
        x = layers.Dropout(0.2)(x)

        # Segunda capa oculta
        x = layers.Dense(self.hidden_dim, activation="relu")(x)
        x = layers.BatchNormalization()(x)
        x = layers.Dropout(0.2)(x)

        # Tercera capa oculta (opcional, puede mejorar convergencia)
        x = layers.Dense(64, activation="relu")(x)

        # Capa de salida: un valor Q para cada acción
        outputs = layers.Dense(self.action_dim, activation="linear")(x)

        model = keras.Model(inputs=inputs, outputs=outputs)
        return model

    def select_action(
        self,
        state: np.ndarray,
        available_actions: Optional[List[int]] = None,
        training: bool = True,
    ) -> int:
        """
        Selecciona una acción (track) usando Epsilon-Greedy.
        
        Con probabilidad epsilon, explora (selecciona aleatoriamente).
        Con probabilidad 1-epsilon, explota (selecciona mejor acción conocida).
        
        Args:
            state: Vector de estado normalizado
            available_actions: Lista de índices de acciones disponibles
            training: Si True, use epsilon-greedy; si False, siempre explota
            
        Returns:
            int: Índice de la acción (track) seleccionada
        """
        if available_actions is None:
            available_actions = list(range(self.action_dim))

        # Exploración
        if training and np.random.random() < self.epsilon:
            return np.random.choice(available_actions)

        # Explotación: predecir Q-values
        state_tensor = tf.expand_dims(state, axis=0)
        q_values = self.q_network(state_tensor, training=False).numpy()[0]

        # Enmascarar acciones no disponibles
        q_values_masked = np.full_like(q_values, -np.inf)
        q_values_masked[available_actions] = q_values[available_actions]

        # Seleccionar mejor acción
        action = np.argmax(q_values_masked)
        return int(action)

    def remember(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        next_state: np.ndarray,
        done: bool,
    ) -> None:
        """
        Guarda una experiencia en el replay buffer.
        
        Args:
            state: Estado inicial
            action: Acción tomada
            reward: Recompensa obtenida
            next_state: Estado siguiente
            done: Si el episodio terminó
        """
        self.memory.append((state, action, reward, next_state, done))

    def replay(self) -> Optional[float]:
        """
        Entrena la red con un mini-batch del replay buffer.
        
        Returns:
            float: Loss del batch, o None si no hay suficientes experiencias
        """
        if len(self.memory) < self.batch_size:
            return None

        # Sample del replay buffer
        batch = np.random.choice(len(self.memory), self.batch_size, replace=False)
        experiences = [self.memory[i] for i in batch]

        states, actions, rewards, next_states, dones = zip(*experiences)

        states = np.array(states, dtype=np.float32)
        next_states = np.array(next_states, dtype=np.float32)
        rewards = np.array(rewards, dtype=np.float32)
        actions = np.array(actions, dtype=np.int32)
        dones = np.array(dones, dtype=np.float32)

        # Calcular target Q-values usando target network
        target_q_values = self.target_network.predict(next_states, verbose=0)
        max_target_q_values = np.max(target_q_values, axis=1)

        # Bellman equation: Q(s,a) = r + gamma * max(Q(s',a'))
        targets = rewards + (1 - dones) * self.gamma * max_target_q_values

        # Entrenar la red principal
        with tf.GradientTape() as tape:
            predictions = self.q_network(states, training=True)
            one_hot_actions = tf.one_hot(actions, self.action_dim)

            # Calcular loss solo para las acciones tomadas
            q_values_for_actions = tf.reduce_sum(predictions * one_hot_actions, axis=1)
            # Usar MSE manualmente: (targets - q_values)^2
            loss = tf.square(targets - q_values_for_actions)
            loss = tf.reduce_mean(loss)

        # Backpropagation
        gradients = tape.gradient(loss, self.q_network.trainable_variables)
        self.optimizer.apply_gradients(
            zip(gradients, self.q_network.trainable_variables)
        )

        self.steps += 1

        # Decay epsilon
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

        return float(loss.numpy())

    def _update_target_network(self) -> None:
        """
        Actualiza target network con pesos de la red principal.
        
        Esto estabiliza el entrenamiento.
        """
        self.target_network.set_weights(self.q_network.get_weights())

    def update_target_network(self, update_frequency: int = 1000) -> None:
        """
        Actualiza target network cada cierto número de steps.
        
        Args:
            update_frequency: Cada cuántos steps actualizar
        """
        if self.steps % update_frequency == 0:
            self._update_target_network()

    def save_model(self, filepath: Optional[str] = None) -> None:
        """
        Guarda el modelo a disco.
        
        Args:
            filepath: Ruta donde guardar (usa self.model_path si no se especifica)
        """
        filepath = filepath or self.model_path
        self.q_network.save(filepath)
        logger.info(f"Modelo guardado en: {filepath}")

    def load_model(self, filepath: Optional[str] = None) -> None:
        """
        Carga un modelo previamente entrenado.
        
        Args:
            filepath: Ruta del modelo a cargar
        """
        filepath = filepath or self.model_path
        self.q_network = keras.models.load_model(filepath)
        self._update_target_network()
        logger.info(f"Modelo cargado desde: {filepath}")

    def get_q_values(self, state: np.ndarray) -> np.ndarray:
        """
        Obtiene los Q-values de un estado.
        
        Útil para debugging y análisis.
        
        Args:
            state: Vector de estado
            
        Returns:
            np.ndarray: Array de Q-values para cada acción
        """
        state_tensor = tf.expand_dims(state, axis=0)
        q_values = self.q_network(state_tensor, training=False).numpy()[0]
        return q_values

    def get_best_action(
        self,
        state: np.ndarray,
        available_actions: Optional[List[int]] = None,
        top_k: int = 1,
    ) -> List[Tuple[int, float]]:
        """
        Obtiene las mejores acciones ordenadas por Q-value.
        
        Args:
            state: Vector de estado
            available_actions: Acciones disponibles
            top_k: Número de mejores acciones a retornar
            
        Returns:
            List[Tuple[int, float]]: Lista de (action_idx, q_value) ordenada
        """
        if available_actions is None:
            available_actions = list(range(self.action_dim))

        q_values = self.get_q_values(state)

        # Filtrar solo acciones disponibles
        available_q_values = [
            (action, q_values[action]) for action in available_actions
        ]

        # Ordenar por Q-value descendente
        available_q_values.sort(key=lambda x: x[1], reverse=True)

        return available_q_values[:top_k]

    def reset_epsilon(self, epsilon: float = 1.0) -> None:
        """
        Resetea epsilon (útil para evaluar después de entrenar).
        """
        self.epsilon = epsilon

    def summary(self) -> str:
        """
        Retorna un resumen del agente.
        """
        return (
            f"DQN Agent Summary:\n"
            f"  State Dim: {self.state_dim}\n"
            f"  Action Dim: {self.action_dim}\n"
            f"  Learning Rate: {self.learning_rate}\n"
            f"  Gamma (Discount): {self.gamma}\n"
            f"  Epsilon: {self.epsilon:.4f}\n"
            f"  Memory Size: {len(self.memory)}/{self.memory_size}\n"
            f"  Total Steps: {self.steps}\n"
            f"  Total Episodes: {self.episodes}\n"
        )


class TrainingLoop:
    """
    Loop de entrenamiento para el agente DQN.
    
    Coordina la interacción entre el agente, el entorno, y el almacenamiento
    de experiencias para un entrenamiento continuo.
    """

    def __init__(
        self,
        agent: DQNAgent,
        episodes: int = 100,
        max_steps_per_episode: int = 50,
        target_update_frequency: int = 1000,
    ):
        """
        Inicializa el loop de entrenamiento.
        
        Args:
            agent: Instancia de DQNAgent
            episodes: Número de episodios a entrenar
            max_steps_per_episode: Máximo de pasos por episodio
            target_update_frequency: Cada cuántos steps actualizar target network
        """
        self.agent = agent
        self.episodes = episodes
        self.max_steps_per_episode = max_steps_per_episode
        self.target_update_frequency = target_update_frequency
        self.episode_rewards = []
        self.episode_losses = []

    def train(self) -> Dict[str, List[float]]:
        """
        Ejecuta el loop de entrenamiento (sobre episodios).
        
        Returns:
            Dict con histórico de rewards y losses
        """
        logger.info(f"Iniciando entrenamiento por {self.episodes} episodios...")

        for episode in range(self.episodes):
            episode_reward = 0
            episode_loss_values = []

            # Cada episodio genera experiencias
            self.agent.episodes += 1

            # Al final del episodio, entrenar con replay
            for step in range(min(len(self.agent.memory), 10)):
                loss = self.agent.replay()
                if loss is not None:
                    episode_loss_values.append(loss)

            self.episode_rewards.append(episode_reward)
            avg_loss = np.mean(episode_loss_values) if episode_loss_values else 0
            self.episode_losses.append(avg_loss)

            # Actualizar target network
            self.agent.update_target_network(self.target_update_frequency)

            if (episode + 1) % 10 == 0:
                avg_reward = np.mean(self.episode_rewards[-10:])
                logger.info(
                    f"Episodio {episode + 1}/{self.episodes} - "
                    f"Avg Reward: {avg_reward:.4f}, Loss: {avg_loss:.4f}, "
                    f"Epsilon: {self.agent.epsilon:.4f}"
                )

        logger.info("Entrenamiento completado!")
        return {
            "rewards": self.episode_rewards,
            "losses": self.episode_losses,
        }


# Instancia global del agente
_agent_instance = None


def get_agent(**kwargs) -> DQNAgent:
    """
    Obtiene o crea la instancia global del agente DQN.
    """
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = DQNAgent(**kwargs)
    return _agent_instance
