"""profiles, signals, sync state, jobs and embeddings
Revision ID: 0002_intelligence
Revises: 0001_initial
"""
from alembic import op
import sqlalchemy as sa
revision = "0002_intelligence"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("profiles", sa.Column("id",sa.String(64),primary_key=True), sa.Column("name",sa.String(200),nullable=False), sa.Column("is_default",sa.Boolean(),nullable=False,server_default=sa.text("0")), sa.Column("created_at",sa.DateTime(),nullable=False))
    op.create_index("ix_profiles_is_default","profiles",["is_default"])
    op.create_table("user_signals", sa.Column("id",sa.String(64),primary_key=True), sa.Column("profile_id",sa.String(64),sa.ForeignKey("profiles.id",ondelete="CASCADE"),nullable=False), sa.Column("track_id",sa.String(64),sa.ForeignKey("tracks.id",ondelete="CASCADE")), sa.Column("signal",sa.String(32),nullable=False), sa.Column("value",sa.Float(),nullable=False,server_default=sa.text("1")), sa.Column("metadata_json",sa.Text()), sa.Column("created_at",sa.DateTime(),nullable=False))
    for ix,col in [("ix_user_signals_profile_id","profile_id"),("ix_user_signals_track_id","track_id"),("ix_user_signals_signal","signal"),("ix_user_signals_created_at","created_at")]: op.create_index(ix,"user_signals",[col])
    op.create_table("provider_sync_state", sa.Column("id",sa.String(64),primary_key=True), sa.Column("profile_id",sa.String(64),sa.ForeignKey("profiles.id",ondelete="CASCADE")), sa.Column("provider",sa.String(64),nullable=False), sa.Column("resource",sa.String(128),nullable=False), sa.Column("cursor",sa.Text()), sa.Column("last_success_at",sa.DateTime()), sa.Column("last_error",sa.Text()), sa.UniqueConstraint("profile_id","provider","resource",name="uq_provider_sync"))
    op.create_index("ix_provider_sync_state_profile_id","provider_sync_state",["profile_id"]); op.create_index("ix_provider_sync_state_provider","provider_sync_state",["provider"]); op.create_index("ix_provider_sync_state_resource","provider_sync_state",["resource"])
    op.create_table("background_jobs", sa.Column("id",sa.String(64),primary_key=True), sa.Column("job_type",sa.String(128),nullable=False), sa.Column("status",sa.String(32),nullable=False,server_default="queued"), sa.Column("priority",sa.Integer(),nullable=False,server_default=sa.text("50")), sa.Column("payload_json",sa.Text()), sa.Column("attempts",sa.Integer(),nullable=False,server_default=sa.text("0")), sa.Column("error",sa.Text()), sa.Column("created_at",sa.DateTime(),nullable=False), sa.Column("started_at",sa.DateTime()), sa.Column("finished_at",sa.DateTime()))
    op.create_index("ix_background_jobs_job_type","background_jobs",["job_type"]); op.create_index("ix_background_jobs_status","background_jobs",["status"]); op.create_index("ix_background_jobs_priority","background_jobs",["priority"]); op.create_index("ix_background_jobs_created_at","background_jobs",["created_at"])
    op.create_table("track_embeddings", sa.Column("id",sa.String(64),primary_key=True), sa.Column("track_id",sa.String(64),sa.ForeignKey("tracks.id",ondelete="CASCADE"),nullable=False), sa.Column("model",sa.String(128),nullable=False), sa.Column("vector_json",sa.Text(),nullable=False), sa.Column("created_at",sa.DateTime(),nullable=False), sa.Column("updated_at",sa.DateTime(),nullable=False), sa.UniqueConstraint("track_id",name="uq_track_embedding_track"))
    op.create_index("ix_track_embeddings_track_id","track_embeddings",["track_id"])

def downgrade():
    for t in ["track_embeddings","background_jobs","provider_sync_state","user_signals","profiles"]: op.drop_table(t)
