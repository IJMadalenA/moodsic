"""Seed synthetic interactions for offline development and RL experiments."""

from __future__ import annotations

import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.interactions.models import Interaction
from apps.interactions.services.reward_service import get_reward_service
from apps.music.models import Album, Artist, Track

User = get_user_model()


class Command(BaseCommand):
    help = "Generate synthetic interactions without calling external APIs."

    def add_arguments(self, parser):
        parser.add_argument("--users", type=int, default=3)
        parser.add_argument("--tracks", type=int, default=30)
        parser.add_argument("--interactions", type=int, default=300)
        parser.add_argument("--seed", type=int, default=42)

    def handle(self, *args, **options):
        rng = random.Random(options["seed"])
        users = self._ensure_users(options["users"])
        tracks = self._ensure_tracks(options["tracks"], rng)

        reward_service = get_reward_service()
        feedback_choices = [
            "completed",
            "skip",
            "skip_immediate",
            "replay",
            "added_to_playlist",
        ]

        created = 0
        for idx in range(options["interactions"]):
            user = rng.choice(users)
            track = rng.choice(tracks)
            feedback = rng.choices(
                feedback_choices,
                weights=[50, 25, 10, 10, 5],
                k=1,
            )[0]

            track_seconds = max(30, int(track.duration_ms / 1000))
            if feedback == "completed":
                play_duration = int(track_seconds * rng.uniform(0.85, 1.0))
            elif feedback == "skip_immediate":
                play_duration = int(track_seconds * rng.uniform(0.01, 0.07))
            elif feedback == "skip":
                play_duration = int(track_seconds * rng.uniform(0.1, 0.5))
            else:
                play_duration = int(track_seconds * rng.uniform(0.4, 1.0))

            reward = reward_service.calculate_interaction_reward(
                user_feedback=feedback,
                user=user,
                track=track,
                weather_id=None,
                news_ids=None,
            )

            started_at = timezone.now() - timedelta(
                days=rng.randint(0, 14),
                hours=rng.randint(0, 23),
                minutes=rng.randint(0, 59),
            )
            Interaction.objects.create(
                user=user,
                track=track,
                feedback=feedback,
                play_duration=play_duration,
                track_duration=track_seconds,
                reward=reward,
                session_id=f"offline_{user.id}_{idx // 10}",
                started_at=started_at,
            )
            created += 1

        self.stdout.write(
            self.style.SUCCESS(f"Created {created} synthetic interactions.")
        )

    @staticmethod
    def _ensure_users(count: int):
        users = list(User.objects.all()[:count])
        next_idx = len(users)
        while len(users) < count:
            next_idx += 1
            users.append(
                User.objects.create_user(
                    username=f"offline_user_{next_idx}",
                    email=f"offline_user_{next_idx}@example.com",
                    password="offline-pass-123",
                )
            )
        return users

    @staticmethod
    def _ensure_tracks(count: int, rng: random.Random):
        tracks = list(Track.objects.prefetch_related("artists").all()[:count])
        if len(tracks) >= count:
            return tracks

        album, _ = Album.objects.get_or_create(
            spotify_id="offline_album_1",
            defaults={"name": "Offline Album", "release_date": "2026-01-01"},
        )

        artists = []
        for idx, genre in enumerate(["pop", "rock", "electronic", "indie"], start=1):
            artist, _ = Artist.objects.get_or_create(
                spotify_id=f"offline_artist_{idx}",
                defaults={"name": f"Offline Artist {idx}", "genres": [genre]},
            )
            artists.append(artist)

        next_idx = len(tracks)
        while len(tracks) < count:
            next_idx += 1
            track, _ = Track.objects.get_or_create(
                spotify_id=f"offline_track_{next_idx}",
                defaults={
                    "name": f"Offline Track {next_idx}",
                    "album": album,
                    "duration_ms": rng.randint(120000, 260000),
                    "explicit": False,
                    "track_number": next_idx,
                    "popularity": rng.randint(20, 90),
                    "uri": f"spotify:track:offline_track_{next_idx}",
                },
            )
            track.artists.set([rng.choice(artists)])
            tracks.append(track)

        return tracks
