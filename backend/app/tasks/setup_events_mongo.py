"""Apply the reviewed Mongo schema/indexes. No document writes or deletes."""
import json
from pathlib import Path

from pymongo import ASCENDING, DESCENDING

from app.core.config import get_settings
from app.db.mongo import get_mongo_client, close_mongo


def setup():
    settings = get_settings()
    if not settings.mongodb_url.get_secret_value():
        raise RuntimeError('MONGODB_URL is not configured')
    schema = json.loads((Path(__file__).resolve().parents[3] / 'database/mongodb/user_events.schema.json').read_text(encoding='utf-8'))
    db = get_mongo_client()[settings.mongodb_database]
    validator = {'$and': [{'$jsonSchema': schema}, {'$expr': {'$eq': ['$_id', '$event_id']}}]}
    if 'user_events' not in db.list_collection_names():
        db.create_collection('user_events', validator=validator, validationLevel='strict', validationAction='error')
    else:
        db.command('collMod', 'user_events', validator=validator, validationLevel='strict', validationAction='error')
    col = db.user_events
    col.create_index([('event_id', ASCENDING)], name='uq_event_id', unique=True)
    for field in ('user_id', 'session_id', 'event_type', 'content_id'):
        col.create_index([(field, ASCENDING), ('occurred_at', DESCENDING)], name=f'ix_{field}_time')
    print(f'Configured {settings.mongodb_database}.user_events: validator and indexes; documents unchanged')


if __name__ == '__main__':
    try:
        setup()
    finally:
        close_mongo()
