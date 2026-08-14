import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Text, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

def uid() -> str:
    return uuid.uuid4().hex

def now() -> datetime:
    return datetime.now(timezone.utc)

class Artist(Base):
    __tablename__ = "artists"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(500), index=True)
    normalized_name: Mapped[str] = mapped_column(String(500), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

class Album(Base):
    __tablename__ = "albums"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=uid)
    title: Mapped[str] = mapped_column(String(500), index=True)
    artist_id: Mapped[str | None] = mapped_column(ForeignKey("artists.id"), nullable=True)
    release_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    artwork_url: Mapped[str | None] = mapped_column(Text, nullable=True)

class Track(Base):
    __tablename__ = "tracks"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=uid)
    title: Mapped[str] = mapped_column(String(500), index=True)
    normalized_title: Mapped[str] = mapped_column(String(500), index=True)
    artist_id: Mapped[str | None] = mapped_column(ForeignKey("artists.id"), nullable=True, index=True)
    album_id: Mapped[str | None] = mapped_column(ForeignKey("albums.id"), nullable=True, index=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    artwork_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    isrc: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class AudioFeature(Base):
    __tablename__ = "audio_features"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=uid)
    track_id: Mapped[str] = mapped_column(ForeignKey("tracks.id", ondelete="CASCADE"), unique=True, index=True)
    model_version: Mapped[str] = mapped_column(String(64), default="heuristic-v1")
    bpm: Mapped[float | None] = mapped_column(Float, nullable=True)
    key: Mapped[str | None] = mapped_column(String(32), nullable=True)
    energy: Mapped[float | None] = mapped_column(Float, nullable=True)
    danceability: Mapped[float | None] = mapped_column(Float, nullable=True)
    acousticness: Mapped[float | None] = mapped_column(Float, nullable=True)
    loudness: Mapped[float | None] = mapped_column(Float, nullable=True)
    mood: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source: Mapped[str] = mapped_column(String(64), default="metadata")
    raw_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

class TrackSource(Base):
    __tablename__ = "track_sources"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=uid)
    track_id: Mapped[str] = mapped_column(ForeignKey("tracks.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(64), index=True)
    provider_id: Mapped[str] = mapped_column(String(500), index=True)
    uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    playback_kind: Mapped[str | None] = mapped_column(String(64), nullable=True)
    available: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (UniqueConstraint("provider", "provider_id", name="uq_track_source_provider_id"),)

class Playlist(Base):
    __tablename__ = "playlists"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    artwork_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

class PlaylistItem(Base):
    __tablename__ = "playlist_items"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=uid)
    playlist_id: Mapped[str] = mapped_column(ForeignKey("playlists.id", ondelete="CASCADE"), index=True)
    track_id: Mapped[str] = mapped_column(ForeignKey("tracks.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer, index=True)
    preferred_source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=now)

class PlayEvent(Base):
    __tablename__ = "play_events"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=uid)
    track_id: Mapped[str] = mapped_column(ForeignKey("tracks.id", ondelete="CASCADE"), index=True)
    profile_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    seconds: Mapped[int] = mapped_column(Integer, default=0)
    event_type: Mapped[str] = mapped_column(String(32), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)

class Profile(Base):
    __tablename__ = "profiles"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

class UserSignal(Base):
    __tablename__ = "user_signals"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=uid)
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    track_id: Mapped[str | None] = mapped_column(ForeignKey("tracks.id", ondelete="CASCADE"), nullable=True, index=True)
    signal: Mapped[str] = mapped_column(String(32), index=True)
    value: Mapped[float] = mapped_column(Float, default=1.0)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)

class IntegrationAccount(Base):
    __tablename__ = "integration_accounts"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=uid)
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(64), index=True)
    provider_user_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    access_token: Mapped[str] = mapped_column(Text)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)
    __table_args__ = (UniqueConstraint("profile_id", "provider", name="uq_integration_profile_provider"),)

class OAuthState(Base):
    __tablename__ = "oauth_states"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=uid)
    state: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    provider: Mapped[str] = mapped_column(String(64), index=True)
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    code_verifier: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)


class ProviderSyncState(Base):
    __tablename__ = "provider_sync_state"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=uid)
    profile_id: Mapped[str | None] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(64), index=True)
    resource: Mapped[str] = mapped_column(String(128), index=True)
    cursor: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    __table_args__ = (UniqueConstraint("profile_id", "provider", "resource", name="uq_provider_sync"),)



class ExternalCollection(Base):
    __tablename__ = "external_collections"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=uid)
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(64), index=True)
    provider_id: Mapped[str] = mapped_column(String(500), index=True)
    local_playlist_id: Mapped[str] = mapped_column(ForeignKey("playlists.id", ondelete="CASCADE"), unique=True, index=True)
    kind: Mapped[str] = mapped_column(String(32), default="playlist")
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    __table_args__ = (UniqueConstraint("profile_id", "provider", "provider_id", name="uq_external_collection"),)

class BackgroundJob(Base):
    __tablename__ = "background_jobs"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=uid)
    job_type: Mapped[str] = mapped_column(String(128), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True, default="queued")
    priority: Mapped[int] = mapped_column(Integer, default=50)
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

class TrackEmbedding(Base):
    __tablename__ = "track_embeddings"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=uid)
    track_id: Mapped[str] = mapped_column(ForeignKey("tracks.id", ondelete="CASCADE"), unique=True, index=True)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    vector_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

class Lyrics(Base):
    __tablename__ = "lyrics"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=uid)
    track_id: Mapped[str] = mapped_column(ForeignKey("tracks.id", ondelete="CASCADE"), unique=True, index=True)
    plain_lyrics: Mapped[str | None] = mapped_column(Text, nullable=True)
    synced_lyrics: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    offset_ms: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

class RecommendationCandidate(Base):
    __tablename__ = "recommendation_candidates"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=uid)
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    track_id: Mapped[str] = mapped_column(ForeignKey("tracks.id", ondelete="CASCADE"), index=True)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    reason_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)
    __table_args__ = (UniqueConstraint("profile_id", "track_id", name="uq_recommendation_profile_track"),)

class PlayerState(Base):
    __tablename__ = "player_states"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=uid)
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), unique=True, index=True)
    current_item_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_playing: Mapped[bool] = mapped_column(Boolean, default=False)
    position_ms: Mapped[int] = mapped_column(Integer, default=0)
    volume: Mapped[float] = mapped_column(Float, default=1.0)
    shuffle: Mapped[bool] = mapped_column(Boolean, default=False)
    repeat: Mapped[str] = mapped_column(String(16), default="off")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

class PlayerQueueItem(Base):
    __tablename__ = "player_queue_items"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=uid)
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    track_id: Mapped[str] = mapped_column(ForeignKey("tracks.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer, index=True)
    preferred_source: Mapped[str | None] = mapped_column(String(64), nullable=True)
