from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.platform.settings import get_settings


class Base(DeclarativeBase):
    pass


@lru_cache
def session_factory() -> sessionmaker[Session]:
    engine = create_engine(
        get_settings().database_url.get_secret_value(), pool_pre_ping=True, hide_parameters=True
    )
    return sessionmaker(engine, expire_on_commit=False)


def get_session():
    with session_factory()() as session:
        yield session
