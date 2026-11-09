from datetime import datetime, timezone

from app.db.mongo import user_events

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
    user_events().update_one({'_id': event.event_id}, {'$setOnInsert': document}, upsert=True)
