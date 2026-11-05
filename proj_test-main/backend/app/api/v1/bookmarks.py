from uuid import uuid4
from fastapi import APIRouter, Depends
from app.api.deps import current_user, get_store
from app.schemas import ContentPage
from app.services.catalog import CatalogService

router = APIRouter(prefix='/bookmarks', tags=['bookmarks'])


@router.get('', response_model=ContentPage)
def listing(store=Depends(get_store), user=Depends(current_user)):
    items = CatalogService(store).serialize(store.bookmarks(user.id), user)
    return ContentPage(items=items, total=len(items), size=100)


def set_state(content_id, enabled, store, user):
    CatalogService(store).require(content_id)
    store.set_bookmark(user.id, content_id, enabled)
    store.event({'event_id': str(uuid4()), 'event_type': 'bookmark_add' if enabled else 'bookmark_remove',
                 'user_id': user.id, 'content_id': content_id})
    return {'bookmarked': enabled}


@router.put('/{content_id}')
def add(content_id: int, store=Depends(get_store), user=Depends(current_user)):
    return set_state(content_id, True, store, user)


@router.delete('/{content_id}')
def remove(content_id: int, store=Depends(get_store), user=Depends(current_user)):
    return set_state(content_id, False, store, user)
