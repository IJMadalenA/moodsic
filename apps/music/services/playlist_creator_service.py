import logging
from typing import Any

from apps.music.services.spotify_music_service import SpotifyMusicService

logger = logging.getLogger(__name__)


class PlaylistCreatorService:
    """
    High-level service for intelligent playlist creation and management.
    Inspired by the 'playlist_creator' pattern from the Spotify skill.
    """

    def __init__(self, spotify_service: SpotifyMusicService):
        self.spotify_service = spotify_service

    def create_atomic_playlist(
        self, name: str, description: str, track_uris: list[str], public: bool = False
    ) -> dict | None:
        """
        Creates a playlist and adds tracks in one atomic operation.
        """
        logger.info(
            f"Starting atomic playlist creation: {name} ({len(track_uris)} tracks)"
        )

        # 1. Create the playlist
        playlist = self.spotify_service.create_playlist(
            name=name, description=description, public=public
        )

        if not playlist:
            logger.error("Failed to create playlist base.")
            return None

        playlist_id = playlist.get("id")

        # 2. Add tracks
        if track_uris:
            success = self.spotify_service.add_tracks_to_playlist(
                playlist_id, track_uris
            )
            if not success:
                logger.warning(
                    f"Playlist {playlist_id} created, but some tracks might not have been added."
                )

        logger.info(f"Atomic creation finished for playlist: {playlist_id}")
        return playlist

    def generate_from_recommendations(
        self,
        name: str,
        seed_tracks: list[str] | None = None,
        seed_artists: list[str] | None = None,
        seed_genres: list[str] | None = None,
        description: str = "Generated from Spotify Recommendations",
        public: bool = False,
        limit: int = 20,
    ) -> dict | None:
        """
        Generates a new playlist using Spotify's recommendation engine.
        """
        logger.info(f"Generating recommendation-based playlist: {name}")

        # 1. Get recommendations
        tracks = self.spotify_service.get_recommendations(
            seed_tracks=seed_tracks,
            seed_artists=seed_artists,
            seed_genres=seed_genres,
            limit=limit,
        )

        if not tracks:
            logger.warning("No recommendations found with provided seeds.")
            return None

        track_uris = [t.get("uri") for t in tracks if t.get("uri")]

        # 2. Create and fill playlist
        return self.create_atomic_playlist(
            name=name, description=description, track_uris=track_uris, public=public
        )

    def get_playlist_details_with_stats(self, playlist_id: str) -> dict[str, Any]:
        """
        Retrieves a playlist and its calculated statistics.
        """
        return self.spotify_service.get_playlist_stats(playlist_id)
