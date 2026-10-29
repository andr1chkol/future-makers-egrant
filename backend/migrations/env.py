from alembic import context
from app.platform import models  # noqa: F401
from app.platform.database import Base
from app.platform.settings import get_settings
from sqlalchemy import create_engine

engine = create_engine(get_settings().database_url.get_secret_value(), hide_parameters=True)
with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()
