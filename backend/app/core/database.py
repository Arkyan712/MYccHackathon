import os
import shutil
import logging

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

logger = logging.getLogger(__name__)

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# Enable WAL mode for better concurrency and crash safety
@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        yield session


def backup_db():
    """Create a timestamped backup of the database file."""
    db_path = settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "")
    if not os.path.isabs(db_path):
        db_path = os.path.join(os.path.dirname(__file__), "..", "..", db_path)
    db_path = os.path.normpath(db_path)
    if os.path.exists(db_path):
        backup_dir = os.path.join(os.path.dirname(db_path), "db_backups")
        os.makedirs(backup_dir, exist_ok=True)
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(backup_dir, f"app_{ts}.db")
        shutil.copy2(db_path, backup_path)
        logger.info("DB backup created: %s", backup_path)
        # Keep only last 5 backups
        backups = sorted(os.listdir(backup_dir))
        while len(backups) > 5:
            os.remove(os.path.join(backup_dir, backups[0]))
            backups.pop(0)
