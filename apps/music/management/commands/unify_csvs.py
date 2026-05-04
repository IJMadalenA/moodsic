"""
Unifica los CSVs fuente en un solo CSV maestro (unified_tracks.csv).

Estrategia:
- spotify_data.csv como base (1.16M filas)
- Left join secuencial con otras fuentes por track_id
- Normaliza tipos (key string->int, bool, arrays JSON)
- Resuelve conflictos: primer valor gana, excepto popularity donde se toma el maximo
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from django.core.management.base import BaseCommand

DATASETS_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "ml" / "datasets"

KEY_MAP_STR_TO_INT = {
    "c": 0,
    "c#": 1,
    "db": 1,
    "d": 2,
    "d#": 3,
    "eb": 3,
    "e": 4,
    "f": 5,
    "f#": 6,
    "gb": 6,
    "g": 7,
    "g#": 8,
    "ab": 8,
    "a": 9,
    "a#": 10,
    "bb": 10,
    "b": 11,
}

MODE_MAP = {"major": 1, "minor": 0}


def _extract_track_id(value: str) -> str:
    if "spotify:track:" in str(value):
        return str(value).split("spotify:track:")[1]
    return str(value)


def _normalize_spotifyfeatures(df: pd.DataFrame) -> pd.DataFrame:
    if "key" in df.columns:
        df["key"] = (
            df["key"].astype(str).str.strip().str.lower().map(KEY_MAP_STR_TO_INT).fillna(-1).astype(int)
        )
    if "mode" in df.columns:
        df["mode"] = (
            df["mode"].astype(str).str.strip().str.lower().map(MODE_MAP).fillna(0).astype(int)
        )
    if "track_id" in df.columns:
        df["track_id"] = df["track_id"].apply(_extract_track_id)
    return df


def _normalize_spotify_data(df: pd.DataFrame) -> pd.DataFrame:
    column_rename = {
        "artist_name": "artist_name",
        "track_name": "name",
        "track_id": "track_id",
        "popularity": "popularity",
        "year": "year",
        "genre": "genre",
        "danceability": "danceability",
        "energy": "energy",
        "key": "key",
        "loudness": "loudness",
        "mode": "mode",
        "speechiness": "speechiness",
        "acousticness": "acousticness",
        "instrumentalness": "instrumentalness",
        "liveness": "liveness",
        "valence": "valence",
        "tempo": "tempo",
        "duration_ms": "duration_ms",
        "time_signature": "time_signature",
    }
    df = df.rename(columns={k: v for k, v in column_rename.items() if k in df.columns})
    if "track_id" in df.columns:
        df["track_id"] = df["track_id"].apply(_extract_track_id)
    return df


def _normalize_main_dataset(df: pd.DataFrame) -> pd.DataFrame:
    column_rename = {
        "track_uri": "track_id",
        "name": "name",
        "artists_names": "artists_names",
        "popularity": "popularity",
        "album_type": "album_type",
        "is_playable": "is_playable",
        "release_date": "release_date",
        "analysis_url": "analysis_url",
    }
    df = df.rename(columns={k: v for k, v in column_rename.items() if k in df.columns})
    if "track_id" in df.columns:
        df["track_id"] = df["track_id"].apply(_extract_track_id)
    columns_to_keep = ["track_id", "name", "artists_names", "popularity", "album_type", "is_playable", "release_date", "analysis_url"]
    return df[[c for c in columns_to_keep if c in df.columns]]


def _normalize_dataset(df: pd.DataFrame) -> pd.DataFrame:
    if "track_id" in df.columns:
        df["track_id"] = df["track_id"].apply(_extract_track_id)
    columns_to_keep = ["track_id", "explicit", "track_genre"]
    return df[[c for c in columns_to_keep if c in df.columns]]


def _normalize_spotify_songs(df: pd.DataFrame) -> pd.DataFrame:
    column_rename = {
        "track_id": "track_id",
        "track_name": "name",
        "track_artist": "artist_name",
        "track_popularity": "popularity",
        "playlist_genre": "playlist_genre",
        "playlist_subgenre": "playlist_subgenre",
    }
    df = df.rename(columns={k: v for k, v in column_rename.items() if k in df.columns})
    if "track_id" in df.columns:
        df["track_id"] = df["track_id"].apply(_extract_track_id)
    columns_to_keep = ["track_id", "playlist_genre", "playlist_subgenre"]
    return df[[c for c in columns_to_keep if c in df.columns]]


class Command(BaseCommand):
    help = "Unifica los CSVs fuente en un solo archivo unified_tracks.csv"

    def handle(self, *args, **options):
        self.stdout.write("=== UNIFICACION DE CSVs ===")

        base_path = DATASETS_DIR / "spotify_data.csv"
        if not base_path.exists():
            self.stdout.write(self.style.ERROR(f"No encontrado: {base_path}"))
            return

        file_size_mb = os.path.getsize(base_path) / 1024 / 1024
        self.stdout.write(f"Cargando base: {base_path.name} ({file_size_mb:.0f} MB)...")
        base = pd.read_csv(base_path, low_memory=False)
        self.stdout.write(f"  -> {len(base):,} filas")
        base = _normalize_spotify_data(base)

        md_path = DATASETS_DIR / "main_dataset.csv"
        if md_path.exists():
            self.stdout.write(f"Enriqueciendo con: {md_path.name}...")
            md = _normalize_main_dataset(pd.read_csv(md_path, low_memory=False))
            self.stdout.write(f"  -> {len(md):,} filas")
            for col in md.columns:
                if col == "track_id":
                    continue
                if col in base.columns and col != "popularity":
                    md = md.drop(columns=[col])
            base = base.merge(md, on="track_id", how="left", suffixes=("", "_md"))

        sf_path = DATASETS_DIR / "SpotifyFeatures.csv"
        if sf_path.exists():
            self.stdout.write(f"Enriqueciendo con: {sf_path.name}...")
            sf = _normalize_spotifyfeatures(pd.read_csv(sf_path, low_memory=False))
            self.stdout.write(f"  -> {len(sf):,} filas")
            sf_genre = sf[["track_id", "genre"]].drop_duplicates(subset="track_id", keep="first")
            dup_suffixes = [c for c in base.columns if c.endswith("_x") or c.endswith("_y")]
            if "genre_x" in base.columns:
                base["genre"] = base["genre_x"].fillna("")
            if dup_suffixes:
                base = base.drop(columns=[c for c in dup_suffixes if c != "genre"], errors="ignore")
            base = base.merge(sf_genre, on="track_id", how="left", suffixes=("", "_sf"))

        ds_path = DATASETS_DIR / "dataset.csv"
        if ds_path.exists():
            self.stdout.write(f"Enriqueciendo con: {ds_path.name}...")
            ds = _normalize_dataset(pd.read_csv(ds_path, low_memory=False))
            self.stdout.write(f"  -> {len(ds):,} filas")
            base = base.merge(ds, on="track_id", how="left", suffixes=("", "_ds"))

        ss_path = DATASETS_DIR / "spotify_songs.csv"
        if ss_path.exists():
            self.stdout.write(f"Enriqueciendo con: {ss_path.name}...")
            ss = _normalize_spotify_songs(pd.read_csv(ss_path, low_memory=False))
            self.stdout.write(f"  -> {len(ss):,} filas")
            base = base.merge(ss, on="track_id", how="left", suffixes=("", "_ss"))

        popularity_cols = [c for c in base.columns if c.startswith("popularity")]
        if len(popularity_cols) > 1:
            base["popularity"] = base[popularity_cols].max(axis=1)
            for c in popularity_cols:
                if c != "popularity":
                    base = base.drop(columns=[c])

        audio_feature_cols = [
            "danceability",
            "energy",
            "key",
            "loudness",
            "mode",
            "speechiness",
            "acousticness",
            "instrumentalness",
            "liveness",
            "valence",
            "tempo",
            "time_signature",
            "duration_ms",
        ]
        output_cols = [
            "track_id",
            "name",
            "artist_name",
            "popularity",
            "genre",
            "playlist_genre",
            "playlist_subgenre",
            "track_genre",
            "album_type",
            "release_date",
            "is_playable",
            "explicit",
            "analysis_url",
            "year",
        ] + audio_feature_cols

        available_cols = [c for c in output_cols if c in base.columns]
        result = base[available_cols].copy()

        if "explicit" in result.columns:
            result["explicit"] = (
                result["explicit"]
                .astype(str)
                .str.lower()
                .map({"true": True, "false": False, "1": True, "0": False})
                .fillna(False)
                .astype(bool)
            )
        if "is_playable" in result.columns:
            result["is_playable"] = (
                result["is_playable"]
                .astype(str)
                .str.lower()
                .map({"true": True, "false": False})
                .fillna(True)
                .astype(bool)
            )

        output_path = DATASETS_DIR / "unified_tracks.csv"
        result.to_csv(output_path, index=False)
        size_mb = os.path.getsize(output_path) / 1024 / 1024
        self.stdout.write(
            self.style.SUCCESS(
                f"\nUnificacion completada: {output_path} "
                f"({size_mb:.0f} MB, {len(result):,} filas, {len(available_cols)} columnas)"
            )
        )
