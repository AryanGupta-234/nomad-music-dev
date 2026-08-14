"""provider OAuth connections"""
from alembic import op
import sqlalchemy as sa
revision="0004_integrations"
down_revision="0003_lyrics_recommendations"
branch_labels=None
depends_on=None
def upgrade():
    op.create_table("integration_accounts", sa.Column("id",sa.String(64),primary_key=True), sa.Column("profile_id",sa.String(64),sa.ForeignKey("profiles.id",ondelete="CASCADE"),nullable=False), sa.Column("provider",sa.String(64),nullable=False), sa.Column("provider_user_id",sa.String(255)), sa.Column("access_token",sa.Text(),nullable=False), sa.Column("refresh_token",sa.Text()), sa.Column("expires_at",sa.DateTime()), sa.Column("scope",sa.Text()), sa.Column("metadata_json",sa.Text()), sa.Column("created_at",sa.DateTime(),nullable=False), sa.Column("updated_at",sa.DateTime(),nullable=False), sa.UniqueConstraint("profile_id","provider",name="uq_integration_profile_provider"))
    op.create_index("ix_integration_accounts_profile_id","integration_accounts",["profile_id"]); op.create_index("ix_integration_accounts_provider","integration_accounts",["provider"])
    op.create_table("oauth_states", sa.Column("id",sa.String(64),primary_key=True), sa.Column("state",sa.String(255),nullable=False,unique=True), sa.Column("provider",sa.String(64),nullable=False), sa.Column("profile_id",sa.String(64),sa.ForeignKey("profiles.id",ondelete="CASCADE"),nullable=False), sa.Column("created_at",sa.DateTime(),nullable=False))
    for n in ("state","provider","profile_id","created_at"): op.create_index(f"ix_oauth_states_{n}","oauth_states",[n])
def downgrade(): op.drop_table("oauth_states"); op.drop_table("integration_accounts")
