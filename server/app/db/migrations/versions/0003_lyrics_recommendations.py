"""lyrics and recommendation candidates
Revision ID: 0003_lyrics_recommendations
Revises: 0002_intelligence
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_lyrics_recommendations"
down_revision = "0002_intelligence"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "lyrics",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("track_id", sa.String(64), sa.ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plain_lyrics", sa.Text()),
        sa.Column("synced_lyrics", sa.Text()),
        sa.Column("source", sa.String(64)),
        sa.Column("offset_ms", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("track_id", name="uq_lyrics_track"),
    )
    op.create_index("ix_lyrics_track_id", "lyrics", ["track_id"])
    op.create_table(
        "recommendation_candidates",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("profile_id", sa.String(64), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("track_id", sa.String(64), sa.ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("score", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("reason_json", sa.Text()),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("profile_id", "track_id", name="uq_recommendation_profile_track"),
    )
    op.create_index("ix_recommendation_candidates_profile_id", "recommendation_candidates", ["profile_id"])
    op.create_index("ix_recommendation_candidates_track_id", "recommendation_candidates", ["track_id"])
    op.create_index("ix_recommendation_candidates_generated_at", "recommendation_candidates", ["generated_at"])

def downgrade():
    op.drop_table("recommendation_candidates")
    op.drop_table("lyrics")
