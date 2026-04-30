import logging

from apps.music.models import Album, Artist, Track, TrackAudioFeatures

logger = logging.getLogger(__name__)


class MusicDataService:
    """
    Service to handle persistence of music metadata from external APIs (e.g., Spotify).
    """

    @staticmethod
    def persist_tracks(
        tracks_data, save_audio_features=False, audio_features_data=None
    ):
        """
        Saves a list of track dictionaries into the local database.
        Handles Artists, Albums, and Tracks.

        tracks_data: List of track dictionaries from Spotify API.
        """
        saved_count = 0
        skipped_count = 0
        artist_cache = {}

        if audio_features_data is None:
            audio_features_data = {}

        for track_item in tracks_data:
            try:
                # Handle nested structure if it's from current_user_saved_tracks
                track_data = (
                    track_item.get("track", track_item)
                    if isinstance(track_item, dict)
                    else track_item
                )

                # 1. Get or Create Album
                album_data = track_data.get("album")
                album = None
                if album_data and isinstance(album_data, dict):
                    album_id = album_data.get("id")
                    if album_id:
                        album, _ = Album.objects.get_or_create(
                            spotify_id=album_id,
                            defaults={
                                "name": album_data.get("name", "Unknown Album"),
                                "album_type": album_data.get("album_type", ""),
                                "release_date": album_data.get("release_date") or "",
                            },
                        )
                elif track_data.get("album_id"):
                    # Fallback for flat structures
                    album, _ = Album.objects.get_or_create(
                        spotify_id=track_data.get("album_id"),
                        defaults={
                            "name": track_data.get("album", "Unknown Album"),
                        },
                    )

                # 2. Get or Create Artists
                artists = []
                spotify_artists = track_data.get("artists", [])
                for artist_info in spotify_artists:
                    # FIX: artist_info might be a dict (Spotify API) or a string (some simplified internal formats)
                    if isinstance(artist_info, dict):
                        artist_name = artist_info.get("name")
                        artist_id = artist_info.get("id")
                    else:
                        artist_name = artist_info
                        artist_id = f"local_{artist_name.lower().replace(' ', '_')}"

                    if not artist_name:
                        continue

                    artist_key = artist_name.lower()
                    if artist_key not in artist_cache:
                        artist, _ = Artist.objects.get_or_create(
                            name=artist_name,
                            defaults={"spotify_id": artist_id or f"local_{artist_key}"},
                        )
                        artist_cache[artist_key] = artist
                    artists.append(artist_cache[artist_key])

                # 3. Get or Create Track
                track_id = track_data.get("id")
                if not track_id:
                    continue

                track, created = Track.objects.get_or_create(
                    spotify_id=track_id,
                    defaults={
                        "name": track_data.get("name", "Unknown Track"),
                        "album": album,
                        "duration_ms": track_data.get("duration_ms", 0),
                        "explicit": track_data.get("explicit", False),
                        "popularity": track_data.get("popularity", 0),
                        "preview_url": track_data.get("preview_url") or "",
                        "uri": track_data.get("uri", ""),
                        "track_number": track_data.get("track_number", 0),
                    },
                )

                if artists:
                    track.artists.add(*artists)

                if created:
                    saved_count += 1
                    # 4. Handle Audio Features
                    if save_audio_features and track_id in audio_features_data:
                        features = audio_features_data[track_id]
                        if features:
                            TrackAudioFeatures.objects.get_or_create(
                                track=track,
                                defaults={
                                    "danceability": features.get("danceability") or 0.5,
                                    "energy": features.get("energy") or 0.5,
                                    "key": features.get("key") or 0,
                                    "loudness": features.get("loudness") or -5.0,
                                    "mode": features.get("mode") or 1,
                                    "speechiness": features.get("speechiness") or 0.0,
                                    "acousticness": features.get("acousticness") or 0.0,
                                    "instrumentalness": features.get("instrumentalness")
                                    or 0.0,
                                    "liveness": features.get("liveness") or 0.0,
                                    "valence": features.get("valence") or 0.5,
                                    "tempo": features.get("tempo") or 120.0,
                                    "time_signature": features.get("time_signature")
                                    or 4,
                                },
                            )
                else:
                    skipped_count += 1

            except Exception as e:
                logger.error(f"Error persisting track data: {e}", exc_info=True)
                continue

        return saved_count, skipped_count
