"""external collection mappings"""
from alembic import op
import sqlalchemy as sa

revision = "0006_external_collections"
down_revision = "0005_player_queue"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "external_collections",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("profile_id", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("provider_id", sa.String(length=500), nullable=False),
        sa.Column("local_playlist_id", sa.String(length=64), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False, server_default="playlist"),
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["local_playlist_id"], ["playlists.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("profile_id", "provider", "provider_id", name="uq_external_collection"),
        sa.UniqueConstraint("local_playlist_id", name="uq_external_collection_local_playlist"),
    )
    op.create_index("ix_external_collections_profile_id", "external_collections", ["profile_id"])
    op.create_index("ix_external_collections_provider", "external_collections", ["provider"])
    op.create_index("ix_external_collections_provider_id", "external_collections", ["provider_id"])

def downgrade():
    op.drop_index("ix_external_collections_provider_id", table_name="external_collections")
    op.drop_index("ix_external_collections_provider", table_name="external_collections")
    op.drop_index("ix_external_collections_profile_id", table_name="external_collections")
    op.drop_table("external_collections")
