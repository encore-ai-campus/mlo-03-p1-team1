from datetime import datetime, timezone
import json
import logging
import sys

from app.db.mongo import user_events

logger = logging.getLogger('culturepick.events')
logger.setLevel(logging.INFO)
logger.propagate = False
if not logger.handlers:
    event_handler = logging.StreamHandler(sys.stdout)
    event_handler.setLevel(logging.INFO)
    event_handler.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(event_handler)

SERVER_EVENTS = {'bookmark_add', 'bookmark_remove', 'payment_completed', 'payment_cancelled'}
PROPERTY_KEYS = {'category', 'query_length', 'filter_name', 'filter_value', 'payment_id',
                 'payment_mode', 'quantity', 'amount', 'currency', 'cancelled_amount'}


def event_document(event):
    properties = event.properties or {}
    context = properties.get('_context', {})
    return {
        '_id': event.event_id, 'event_id': event.event_id, 'schema_version': 1,
        'event_type': event.event_type, 'user_id': event.user_id, 'content_id': event.content_id,
        'occurred_at': event.occurred_at.replace(tzinfo=timezone.utc),
        'ingested_at': datetime.now(timezone.utc),
        'source': 'server' if event.event_type in SERVER_EVENTS else 'browser',
        **{key: context.get(key) for key in ('anonymous_id', 'session_id', 'page_path', 'referrer_path')},
        'properties': {key: value for key, value in properties.items() if key in PROPERTY_KEYS},
    }


def deliver(event):
    # Stable _id and setOnInsert: retries after Mongo success / SQL failure cannot duplicate or overwrite.
    document = event_document(event)
    result = user_events().update_one({'_id': event.event_id}, {'$setOnInsert': document}, upsert=True)
    if result.upserted_id is not None:
        # Keep Loki useful for activity counts without copying user/session identifiers or payment details.
        record = {
            'log_type': 'user_event',
            'event_id': str(document['event_id']),
            'schema_version': document['schema_version'],
            'event_type': document['event_type'],
            'content_id': document['content_id'],
            'occurred_at': document['occurred_at'].isoformat(),
            'ingested_at': document['ingested_at'].isoformat(),
            'source': document['source'],
        }
        logger.info('ODDINARY_EVENT %s', json.dumps(record, separators=(',', ':'), ensure_ascii=False))
