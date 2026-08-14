"""audio intelligence features"""
from alembic import op
import sqlalchemy as sa

revision = "0007_audio_intelligence"
down_revision = "0006_external_collections"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "audio_features",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("track_id", sa.String(length=64), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=False, server_default="heuristic-v1"),
        sa.Column("bpm", sa.Float(), nullable=True),
        sa.Column("key", sa.String(length=32), nullable=True),
        sa.Column("energy", sa.Float(), nullable=True),
        sa.Column("danceability", sa.Float(), nullable=True),
        sa.Column("acousticness", sa.Float(), nullable=True),
        sa.Column("loudness", sa.Float(), nullable=True),
        sa.Column("mood", sa.String(length=64), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False, server_default="metadata"),
        sa.Column("raw_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["track_id"], ["tracks.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("track_id", name="uq_audio_features_track"),
    )
    op.create_index("ix_audio_features_track_id", "audio_features", ["track_id"])

def downgrade():
    op.drop_index("ix_audio_features_track_id", table_name="audio_features")
    op.drop_table("audio_features")
