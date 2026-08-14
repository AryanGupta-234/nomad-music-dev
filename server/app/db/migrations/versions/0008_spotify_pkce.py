"""store OAuth PKCE verifier for desktop Spotify auth"""
from alembic import op
import sqlalchemy as sa

revision = "0008_spotify_pkce"
down_revision = "0007_audio_intelligence"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("oauth_states", sa.Column("code_verifier", sa.Text(), nullable=True))

def downgrade():
    op.drop_column("oauth_states", "code_verifier")
