"""One-shot V4 provider library synchronizer.

Run from server/ after OAuth accounts have been connected:
    python -m app.tools.sync_provider_libraries

This is intentionally a validation/admin command. The desktop UI should call the
same service layer when its combined Sync action is wired in.
"""
from __future__ import annotations

import asyncio

from app.core.profiles.service import get_or_create_default
from app.db.session import SessionLocal
from app.services.integrations import sync_all_libraries


async def main() -> None:
    db = SessionLocal()
    try:
        profile = get_or_create_default(db)
        result = await sync_all_libraries(db, profile.id)
        print(result)
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
