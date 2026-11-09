from datetime import datetime, timezone
import json
import logging
import sys
import uuid

from fastapi import APIRouter, Depends
from app.api.deps import current_user, get_store
from app.schemas import ReviewInput, ReviewOut
from app.services.catalog import CatalogService

router = APIRouter(prefix='/contents', tags=['reviews'])
logger = logging.getLogger('culturepick.events')
logger.setLevel(logging.INFO)
logger.propagate = False
if not logger.handlers:
    event_handler = logging.StreamHandler(sys.stdout)
    event_handler.setLevel(logging.INFO)
    event_handler.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(event_handler)


@router.get('/{content_id}/reviews', response_model=list[ReviewOut])
def listing(content_id: int, store=Depends(get_store)):
    CatalogService(store).require(content_id)
    return [ReviewOut(id=r.id, user_id=r.user_id, name=name, rating=r.rating, body=r.body, updated_at=r.updated_at)
            for r, name in store.reviews(content_id)]


@router.put('/{content_id}/reviews/me', response_model=ReviewOut)
def save(content_id: int, data: ReviewInput, store=Depends(get_store), user=Depends(current_user)):
    review = CatalogService(store).save_review(user, content_id, data)
    record = {
        'log_type': 'user_event',
        'event_id': str(uuid.uuid4()),
        'schema_version': 1,
        'event_type': 'review_write',
        'content_id': content_id,
        'occurred_at': datetime.now(timezone.utc).isoformat(),
        'source': 'api',
    }
    logger.info('ODDINARY_EVENT %s', json.dumps(record, separators=(',', ':'), ensure_ascii=False))
    return review


@router.delete('/{content_id}/reviews/me')
def remove(content_id: int, store=Depends(get_store), user=Depends(current_user)):
    return CatalogService(store).delete_review(user, content_id)
