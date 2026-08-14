from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.models import Profile


def get_or_create_default(db: Session):
    p = db.scalar(select(Profile).where(Profile.is_default == True))
    if not p:
        p = Profile(name="Default", is_default=True); db.add(p); db.commit(); db.refresh(p)
    return p
