"""Domain reward service used by interactions workflow.

This keeps reward-related orchestration in the interactions app while reusing
the RL calculator implementation from ml.reward.
"""

from __future__ import annotations

from apps.context.models import NewsContext, WeatherContext
from apps.music.models import Track
from ml.reward import get_reward_calculator


class RewardService:
	"""Calculates normalized rewards based on user feedback and context."""

	def __init__(self):
		self.reward_calculator = get_reward_calculator()

	def calculate_interaction_reward(
		self,
		*,
		user_feedback: str,
		user,
		track: Track,
		weather_id: int | None = None,
		news_ids: list[int] | None = None,
		user_history: dict | None = None,
	) -> float:
		weather_context = self._get_weather_context(weather_id)
		news_context = self._get_news_context(news_ids)
		audio_features = self._get_track_audio_features(track)
		history = user_history or self._get_user_history(user)

		# Include coarse news signal into weather_context dict to avoid changing
		# the lower-level calculator signature while still using external context.
		if news_context:
			weather_context = weather_context or {}
			weather_context.update(
				{
					"news_sentiment": news_context.get("avg_sentiment", 0.0),
					"breaking_news_ratio": news_context.get("breaking_ratio", 0.0),
				}
			)

		raw_reward = self.reward_calculator.calculate_reward(
			user_feedback=user_feedback,
			weather_context=weather_context,
			track_audio_features=audio_features,
			user_history=history,
		)
		return float(self.reward_calculator.normalize_reward(raw_reward))

	@staticmethod
	def _get_weather_context(weather_id: int | None) -> dict | None:
		if not weather_id:
			return None
		weather = WeatherContext.objects.filter(id=weather_id).first()
		if not weather:
			return None
		return {
			"temperature": weather.temperature,
			"humidity": weather.humidity,
			"wind_speed": weather.wind_speed,
			"main_status": weather.main_status,
		}

	@staticmethod
	def _get_news_context(news_ids: list[int] | None) -> dict | None:
		if not news_ids:
			return None
		news_items = list(NewsContext.objects.filter(id__in=news_ids))
		if not news_items:
			return None
		avg_sentiment = sum(item.sentiment_score for item in news_items) / len(news_items)
		breaking_ratio = sum(1 for item in news_items if item.is_breaking) / len(news_items)
		return {
			"count": len(news_items),
			"avg_sentiment": float(avg_sentiment),
			"breaking_ratio": float(breaking_ratio),
		}

	@staticmethod
	def _get_track_audio_features(track: Track) -> dict:
		audio_features = getattr(track, "audio_features", None)
		if not audio_features:
			return {
				"energy": 0.5,
				"danceability": 0.5,
				"valence": 0.5,
				"acousticness": 0.3,
				"instrumentalness": 0.0,
				"liveness": 0.2,
				"loudness": -5,
				"tempo": 120,
				"speechiness": 0.0,
				"key": 0,
				"mode": 1,
				"time_signature": 4,
			}
		return {
			"energy": audio_features.energy,
			"danceability": audio_features.danceability,
			"valence": audio_features.valence,
			"acousticness": audio_features.acousticness,
			"instrumentalness": audio_features.instrumentalness,
			"liveness": audio_features.liveness,
			"loudness": audio_features.loudness,
			"tempo": audio_features.tempo,
			"speechiness": audio_features.speechiness,
			"key": audio_features.key,
			"mode": audio_features.mode,
			"time_signature": audio_features.time_signature,
		}

	@staticmethod
	def _get_user_history(user) -> dict:
		from apps.interactions.models import Interaction

		interactions = list(Interaction.objects.filter(user=user).select_related("track"))
		if not interactions:
			return {
				"skip_rate": 0.3,
				"avg_energy": 0.5,
				"avg_danceability": 0.5,
				"avg_valence": 0.5,
			}

		total = len(interactions)
		skips = sum(1 for i in interactions if i.feedback.startswith("skip"))

		energies, danceabilities, valences = [], [], []
		for interaction in interactions:
			af = getattr(interaction.track, "audio_features", None)
			if af is None:
				continue
			energies.append(af.energy)
			danceabilities.append(af.danceability)
			valences.append(af.valence)

		def avg(values, default):
			return float(sum(values) / len(values)) if values else default

		return {
			"skip_rate": float(skips / total),
			"avg_energy": avg(energies, 0.5),
			"avg_danceability": avg(danceabilities, 0.5),
			"avg_valence": avg(valences, 0.5),
		}


_reward_service_instance: RewardService | None = None


def get_reward_service() -> RewardService:
	global _reward_service_instance
	if _reward_service_instance is None:
		_reward_service_instance = RewardService()
	return _reward_service_instance
