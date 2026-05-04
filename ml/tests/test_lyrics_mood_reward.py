from ml.reward import RewardCalculator


class TestLyricsMoodReward:
    def test_positive_lyrics_give_positive_reward(self):
        calculator = RewardCalculator()
        reward = calculator._calculate_lyrics_mood_reward({"lyrics_sentiment_score": 0.8})
        assert reward > 0

    def test_negative_lyrics_give_negative_reward(self):
        calculator = RewardCalculator()
        reward = calculator._calculate_lyrics_mood_reward({"lyrics_sentiment_score": -0.8})
        assert reward < 0

    def test_neutral_lyrics_give_near_zero(self):
        calculator = RewardCalculator()
        reward = calculator._calculate_lyrics_mood_reward({"lyrics_sentiment_score": 0.0})
        assert abs(reward) < 0.2

    def test_mood_weight_applied(self):
        calculator = RewardCalculator(lyrics_mood_weight=0.3)
        reward = calculator._calculate_lyrics_mood_reward({"lyrics_sentiment_score": 0.5})
        assert abs(reward) <= 0.3

    def test_calculate_reward_includes_lyrics(self):
        calculator = RewardCalculator(lyrics_mood_weight=0.15)
        reward = calculator.calculate_reward(
            user_feedback="completed",
            track_audio_features={"energy": 0.5, "danceability": 0.5, "valence": 0.5},
            lyrics_data={"lyrics_sentiment_score": 0.9, "lyrics_sentiment_label": "positive"},
        )
        assert reward > 1.0

    def test_no_lyrics_no_effect(self):
        calculator = RewardCalculator()
        reward = calculator.calculate_reward(
            user_feedback="completed",
        )
        assert reward == 2.0
