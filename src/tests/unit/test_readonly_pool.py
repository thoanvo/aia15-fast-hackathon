from sqlalchemy.engine import Engine

from config.settings import READONLY_DATABASE_URL
from database.connection import readonly_pool


def test_readonly_engine_is_constructed_from_readonly_database_url():
    assert isinstance(readonly_pool.readonly_engine, Engine)
    assert readonly_pool.readonly_engine.url.database in READONLY_DATABASE_URL
