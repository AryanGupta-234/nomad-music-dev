"""player queue and persistent player state"""
from alembic import op
import sqlalchemy as sa

revision = "0005_player_queue"
down_revision = "0004_integrations"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "player_states",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("profile_id", sa.String(length=64), nullable=False),
        sa.Column("current_item_id", sa.String(length=64), nullable=True),
        sa.Column("is_playing", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("position_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("volume", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("shuffle", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("repeat", sa.String(length=16), nullable=False, server_default="off"),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("profile_id", name="uq_player_state_profile"),
    )
    op.create_index("ix_player_states_profile_id", "player_states", ["profile_id"])
    op.create_table(
        "player_queue_items",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("profile_id", sa.String(length=64), nullable=False),
        sa.Column("track_id", sa.String(length=64), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("preferred_source", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["track_id"], ["tracks.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_player_queue_items_profile_id", "player_queue_items", ["profile_id"])
    op.create_index("ix_player_queue_items_track_id", "player_queue_items", ["track_id"])
    op.create_index("ix_player_queue_items_position", "player_queue_items", ["position"])


def downgrade():
    op.drop_table("player_queue_items")
    op.drop_table("player_states")
