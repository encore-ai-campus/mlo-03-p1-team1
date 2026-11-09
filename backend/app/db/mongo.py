"""Thread-safe PyMongo connection; the URI never reaches the browser or logs."""
from functools import lru_cache

from pymongo import MongoClient
from pymongo.write_concern import WriteConcern

from app.core.config import get_settings


@lru_cache
def get_mongo_client():
    settings = get_settings()
    return MongoClient(settings.mongodb_url.get_secret_value(), appname='CulturePick-events',
                       serverSelectionTimeoutMS=1500, connectTimeoutMS=1500, socketTimeoutMS=2000,
                       tz_aware=True)


def user_events():
    return get_mongo_client()[get_settings().mongodb_database].get_collection(
        'user_events', write_concern=WriteConcern(w=1, j=True, wtimeout=2000))


def close_mongo():
    if get_mongo_client.cache_info().currsize:
        get_mongo_client().close()
        get_mongo_client.cache_clear()
