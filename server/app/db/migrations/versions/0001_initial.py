"""initial operational schema

Revision ID: 0001_initial
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("artists", sa.Column("id",sa.String(64),primary_key=True), sa.Column("name",sa.String(500),nullable=False), sa.Column("normalized_name",sa.String(500),nullable=False), sa.Column("created_at",sa.DateTime(),nullable=False))
    op.create_index("ix_artists_name","artists",["name"]); op.create_index("ix_artists_normalized_name","artists",["normalized_name"])
    op.create_table("albums", sa.Column("id",sa.String(64),primary_key=True), sa.Column("title",sa.String(500),nullable=False), sa.Column("artist_id",sa.String(64),sa.ForeignKey("artists.id")), sa.Column("release_date",sa.String(32)), sa.Column("artwork_url",sa.Text()))
    op.create_index("ix_albums_title","albums",["title"]); op.create_index("ix_albums_artist_id","albums",["artist_id"])
    op.create_table("tracks", sa.Column("id",sa.String(64),primary_key=True), sa.Column("title",sa.String(500),nullable=False), sa.Column("normalized_title",sa.String(500),nullable=False), sa.Column("artist_id",sa.String(64),sa.ForeignKey("artists.id")), sa.Column("album_id",sa.String(64),sa.ForeignKey("albums.id")), sa.Column("duration_ms",sa.Integer()), sa.Column("artwork_url",sa.Text()), sa.Column("isrc",sa.String(64)), sa.Column("created_at",sa.DateTime(),nullable=False), sa.Column("updated_at",sa.DateTime(),nullable=False))
    for ix,col in [("ix_tracks_title","title"),("ix_tracks_normalized_title","normalized_title"),("ix_tracks_artist_id","artist_id"),("ix_tracks_album_id","album_id"),("ix_tracks_isrc","isrc")]: op.create_index(ix,"tracks",[col])
    op.create_table("track_sources", sa.Column("id",sa.String(64),primary_key=True), sa.Column("track_id",sa.String(64),sa.ForeignKey("tracks.id",ondelete="CASCADE"),nullable=False), sa.Column("provider",sa.String(64),nullable=False), sa.Column("provider_id",sa.String(500),nullable=False), sa.Column("uri",sa.Text()), sa.Column("playback_kind",sa.String(64)), sa.Column("available",sa.Boolean(),nullable=False,server_default=sa.text("1")), sa.UniqueConstraint("provider","provider_id",name="uq_track_source_provider_id"))
    op.create_index("ix_track_sources_track_id","track_sources",["track_id"]); op.create_index("ix_track_sources_provider","track_sources",["provider"]); op.create_index("ix_track_sources_provider_id","track_sources",["provider_id"])
    op.create_table("playlists", sa.Column("id",sa.String(64),primary_key=True), sa.Column("name",sa.String(500),nullable=False), sa.Column("description",sa.Text()), sa.Column("artwork_url",sa.Text()), sa.Column("created_at",sa.DateTime(),nullable=False), sa.Column("updated_at",sa.DateTime(),nullable=False))
    op.create_index("ix_playlists_name","playlists",["name"])
    op.create_table("playlist_items", sa.Column("id",sa.String(64),primary_key=True), sa.Column("playlist_id",sa.String(64),sa.ForeignKey("playlists.id",ondelete="CASCADE"),nullable=False), sa.Column("track_id",sa.String(64),sa.ForeignKey("tracks.id",ondelete="CASCADE"),nullable=False), sa.Column("position",sa.Integer(),nullable=False), sa.Column("preferred_source",sa.String(64)), sa.Column("added_at",sa.DateTime(),nullable=False))
    op.create_index("ix_playlist_items_playlist_id","playlist_items",["playlist_id"]); op.create_index("ix_playlist_items_track_id","playlist_items",["track_id"]); op.create_index("ix_playlist_items_position","playlist_items",["position"])
    op.create_table("play_events", sa.Column("id",sa.String(64),primary_key=True), sa.Column("track_id",sa.String(64),sa.ForeignKey("tracks.id",ondelete="CASCADE"),nullable=False), sa.Column("profile_id",sa.String(64)), sa.Column("seconds",sa.Integer(),nullable=False), sa.Column("event_type",sa.String(32),nullable=False), sa.Column("created_at",sa.DateTime(),nullable=False))
    op.create_index("ix_play_events_track_id","play_events",["track_id"]); op.create_index("ix_play_events_profile_id","play_events",["profile_id"]); op.create_index("ix_play_events_event_type","play_events",["event_type"]); op.create_index("ix_play_events_created_at","play_events",["created_at"])

def downgrade():
    for t in ["play_events","playlist_items","playlists","track_sources","tracks","albums","artists"]: op.drop_table(t)
