# Análisis de Datasets CSV

## Modelo actual de Track en la DB

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `spotify_id` | CharField(255) UNIQUE | Spotify track ID |
| `name` | CharField(255) | Nombre de la canción |
| `album` | FK → Album | Álbum asociado |
| `artists` | M2M → Artist | Artistas |
| `duration_ms` | IntegerField | Duración en ms |
| `explicit` | BooleanField | Contenido explícito |
| `popularity` | IntegerField | Popularidad (nullable) |
| `preview_url` | URLField | URL de preview |
| `track_number` | IntegerField | Número de pista |
| `uri` | CharField(255) | URI de Spotify |

### TrackAudioFeatures (1:1 con Track)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `danceability` | FloatField | 0.0 – 1.0 |
| `energy` | FloatField | 0.0 – 1.0 |
| `key` | IntegerField | 0–11 (C=0) |
| `loudness` | FloatField | dB |
| `mode` | IntegerField | 0=minor, 1=major |
| `speechiness` | FloatField | 0.0 – 1.0 |
| `acousticness` | FloatField | 0.0 – 1.0 |
| `instrumentalness` | FloatField | 0.0 – 1.0 |
| `liveness` | FloatField | 0.0 – 1.0 |
| `valence` | FloatField | 0.0 – 1.0 |
| `tempo` | FloatField | BPM |
| `time_signature` | IntegerField | 3/4, 4/4, etc. |

---

## Inventario de archivos CSV

### 1. `spotify_songs.csv` — ⚠️ DUPLICADO de `spotify_songs02.csv`

| Propiedad | Valor |
|-----------|-------|
| **Filas** | 32,833 |
| **Columnas** | 23 |
| **Llave** | `track_id` (string) |

**Columnas:**
```
track_id, track_name, track_artist, track_popularity, track_album_id,
track_album_name, track_album_release_date, playlist_name, playlist_id,
playlist_genre, playlist_subgenre, danceability, energy, key, loudness,
mode, speechiness, acousticness, instrumentalness, liveness, valence,
tempo, duration_ms
```

**Campos únicos (no en otros CSVs):** `playlist_name`, `playlist_id`, `playlist_genre`, `playlist_subgenre`, `track_album_release_date`

---

### 2. `spotify_songs02.csv` — ⚠️ DUPLICADO de `spotify_songs.csv`

| Propiedad | Valor |
|-----------|-------|
| **Filas** | 32,833 |
| **Columnas** | 23 |

Mismos datos. **Se puede eliminar.**

---

### 3. `spotify_data.csv` — Dataset masivo (~1.16M)

| Propiedad | Valor |
|-----------|-------|
| **Filas** | 1,159,764 |
| **Columnas** | 20 |
| **Llave** | `track_id` (string) |

**Columnas:**
```
[unnamed index], artist_name, track_name, track_id, popularity, year,
genre, danceability, energy, key, loudness, mode, speechiness,
acousticness, instrumentalness, liveness, valence, tempo, duration_ms,
time_signature
```

**Campos únicos:** `year`, `genre` (categórico simple: "acoustic", "pop", etc.)

---

### 4. `main_dataset.csv` — Dataset enriquecido con metadatos de artista

| Propiedad | Valor |
|-----------|-------|
| **Filas** | 277,938 |
| **Columnas** | 26 |
| **Llave** | `track_uri` (URI completa: `spotify:track:xxx`) |

**Columnas:**
```
track_uri, name, artists_names (JSON array), popularity, album_type,
is_playable, release_date, artists_uris (JSON array), playlist_uris,
danceability, energy, key, loudness, mode, speechiness, acousticness,
instrumentalness, liveness, valence, tempo, analysis_url, duration_ms,
time_signature, artists_popularities (JSON array), artists_genres (JSON array),
artists_followers (JSON array)
```

**Campos únicos:** `album_type`, `is_playable`, `analysis_url`, `artists_popularities`, `artists_genres`, `artists_followers` (arrays JSON)

**Relación:** Sus campos `artists_uris`, `artists_genres`, `artists_followers` provienen del archivo `artists.csv` (denormalizados).

---

### 5. `artists.csv` — Tabla de lookup de artistas

| Propiedad | Valor |
|-----------|-------|
| **Filas** | 87,246 |
| **Columnas** | 4 |
| **Llave** | `artist_uri` (`spotify:artist:xxx`) |

**Columnas:** `artist_uri, artist_popularity, artist_genres (JSON), artist_followers`

---

### 6. `spotify_millsongdata.csv` — Dataset de letras (Million Song Dataset)

| Propiedad | Valor |
|-----------|-------|
| **Filas** | 2,427,716 |
| **Columnas** | 4 |
| **Llave** | Ninguna (nombres de artista/canción sin ID) |

**Columnas:** `artist, song, link, text`

**Único archivo con letras (lyrics).** No tiene `track_id`, solo nombres textuales. Útil para NLP/análisis de sentimiento, pero difícil de cruzar con otros datasets sin fuzzy matching.

---

### 7. `dataset.csv` — ⚠️ DUPLICADO de `dataset_02.csv` y `dataset_03.csv`

| Propiedad | Valor |
|-----------|-------|
| **Filas** | 114,000 |
| **Columnas** | 21 |
| **Llave** | `track_id` (string) |

**Columnas:**
```
[unnamed index], track_id, artists, album_name, track_name, popularity,
duration_ms, explicit, danceability, energy, key, loudness, mode, speechiness,
acousticness, instrumentalness, liveness, valence, tempo, time_signature, track_genre
```

**Campos únicos:** `explicit`, `track_genre`, `album_name`

---

### 8. `dataset_02.csv` — ⚠️ DUPLICADO de `dataset.csv`

| Propiedad | Valor |
|-----------|-------|
| **Filas** | 114,000 |
| **Columnas** | 21 |

Mismos datos. **Se puede eliminar.**

---

### 9. `dataset_03.csv` — ⚠️ DUPLICADO de `dataset.csv`

| Propiedad | Valor |
|-----------|-------|
| **Filas** | 114,000 |
| **Columnas** | 20 |

Virtualmente idéntico. **Se puede eliminar.**

---

### 10. `songs_normalize.csv` — Subset normalizado de `playlist_2010to2023.csv`

| Propiedad | Valor |
|-----------|-------|
| **Filas** | 2,000 |
| **Columnas** | 17 |
| **Llave** | (sin track_id, solo `artist` + `song`) |

**Columnas:**
```
artist, song, duration_ms, explicit, year, popularity, danceability,
energy, key, loudness, mode, speechiness, acousticness, instrumentalness,
liveness, valence, tempo, genre
```

Relación directa: las primeras 4 canciones son idénticas a las filas de `playlist_2010to2023.csv`.

---

### 11. `SpotifyFeatures.csv` — Dataset grande con `genre` como columna principal

| Propiedad | Valor |
|-----------|-------|
| **Filas** | 232,725 |
| **Columnas** | 18 |
| **Llave** | `track_id` (string) |

**Columnas:**
```
genre, artist_name, track_name, track_id, popularity, acousticness,
danceability, duration_ms, energy, instrumentalness, key, liveness,
loudness, mode, speechiness, tempo, time_signature, valence
```

**⚠️ Atención:** Los valores de `key` son strings (C#, F#, etc.) y `mode` también (Major/Minor), a diferencia de los otros CSVs que usan enteros (0–11, 0/1).

---

### 12. `playlists/final_playlists.csv` — Metadatos de playlists

| Propiedad | Valor |
|-----------|-------|
| **Filas** | 6,085 |
| **Columnas** | 8 |
| **Llave** | `uri` (`spotify:playlist:xxx`) |

**Columnas:** `[Unnamed: 0], uri, name, description, query, author, n_tracks, playlist_followers`

---

### 13. `playlists/playlist_2010to2023.csv` — Tracks con contexto de playlist + año

| Propiedad | Valor |
|-----------|-------|
| **Filas** | 2,400 |
| **Columnas** | 23 |
| **Llave** | `track_id` (string) + `playlist_url` |

**Columnas:**
```
playlist_url, year, track_id, track_name, track_popularity, album,
artist_id, artist_name, artist_genres (JSON), artist_popularity,
danceability, energy, key, loudness, mode, speechiness, acousticness,
instrumentalness, liveness, valence, tempo, duration_ms, time_signature
```

**Campos únicos:** `year`, `artist_id`, `playlist_url`, `artist_genres` (como JSON)

---

### 14. `playlists/playlists.csv` — Mapeo playlist → género

| Propiedad | Valor |
|-----------|-------|
| **Filas** | 38 |
| **Columnas** | 2 |

**Columnas:** `Playlist, Genre`

Pequeño mapeo manual de 38 playlists a géneros (ej: "37i9dQZF1DX0…" → "Dark Trap").

---

### 15. `playlists/genres_v2.csv` — Dump de Spotify API con género

| Propiedad | Valor |
|-----------|-------|
| **Filas** | 42,305 |
| **Columnas** | 22 |
| **Llave** | `id` (track_id) |

**Columnas:**
```
danceability, energy, key, loudness, mode, speechiness, acousticness,
instrumentalness, liveness, valence, tempo, type, id, uri, track_href,
analysis_url, duration_ms, time_signature, genre, song_name,
Unnamed: 0, title
```

**Campos únicos:** `track_href`, `analysis_url` (datos crudos de Spotify API)

---

## Diagrama de relaciones

```
🎯 Núcleo de features de audio (todos comparten):
   danceability, energy, key, loudness, mode, speechiness,
   acousticness, instrumentalness, liveness, valence, tempo

🔗 Llave universal: track_id (string, Spotify ID)

spotify_data.csv (1.16M) ────┐
SpotifyFeatures.csv (232K) ──┤
main_dataset.csv (278K) ─────┤  Todos comparten track_id + audio features
dataset.csv (114K) ──────────┤
playlist_2010to2023.csv (2.4K)┘
    │
    └── songs_normalize.csv (2K) ← subset condensado (sin track_id)

artists.csv (87K) ──→ main_dataset.csv ← artist_uri/artist_genres/artist_followers

playlists/playlists.csv (38) ← playlist ID → genre mapping
playlists/final_playlists.csv (6K) ← metadata de playlists (nombre, followers)

genres_v2.csv (42K) ← dump de Spotify API (incluye track_href, analysis_url)

spotify_millsongdata.csv (2.4M) ← el único con LETRAS (sin track_id)

⚠️ Duplicados a eliminar:
  • spotify_songs02.csv = spotify_songs.csv
  • dataset_02.csv = dataset.csv
  • dataset_03.csv = dataset.csv
```

---

## Recomendaciones para expansión del modelo

### Campos candidatos a agregar a `Track`

| Campo nuevo | Fuente CSV | Tipo sugerido |
|-------------|------------|---------------|
| `genre` | `SpotifyFeatures.csv`, `dataset.csv` | CharField (o FK a Genre) |
| `subgenre` | `spotify_songs.csv` | CharField |
| `release_date` | `main_dataset.csv` | DateField |
| `album_type` | `main_dataset.csv` | CharField (album/single/compilation) |
| `is_playable` | `main_dataset.csv` | BooleanField |

### Campos candidatos a agregar a `TrackAudioFeatures` o modelo aparte

| Campo nuevo | Fuente CSV | Nota |
|-------------|------------|------|
| `year` | `spotify_data.csv`, `playlist_2010to2023.csv` | Año de lanzamiento |
| `analysis_url` | `main_dataset.csv`, `genres_v2.csv` | URL al análisis de Spotify |
| `genre` | `genres_v2.csv` | Si se quiere separado por track |

### Modelo nuevo sugerido: `TrackLyrics`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `track` | FK → Track (o 1:1) | Canción asociada |
| `text` | TextField | Letra completa |
| `source` | CharField | Origen (ej: "mill-song-data") |

Fuente: `spotify_millsongdata.csv` (requiere fuzzy matching por artista + canción).

### Modelo nuevo sugerido: `Genre`

Géneros como entidad propia (no solo string) para permitir relaciones M2M con Track.

---

## Plan de inserción sugerido

1. **Eliminar duplicados** (`spotify_songs02.csv`, `dataset_02.csv`, `dataset_03.csv`)
2. **Fuente primaria para Tracks:** `spotify_data.csv` (1.16M registros, el más completo con year + genre)
3. **Enriquecer con:** `main_dataset.csv` (album_type, is_playable, release_date) vía `track_id`
4. **Audio features:** Ya mapean 1:1 con `TrackAudioFeatures` (todos los CSVs principales)
5. **Letras:** Procesar `spotify_millsongdata.csv` con fuzzy matching artista+canción para asignar a Tracks existentes
6. **Playlists:** `final_playlists.csv` + `playlist_2010to2023.csv` ya tienen soporte parcial en el modelo `Playlist`/`PlaylistTrack`
