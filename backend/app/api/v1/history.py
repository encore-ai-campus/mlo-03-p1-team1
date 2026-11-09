from fastapi import APIRouter, Depends, HTTPException
from app.api.deps import current_user, get_store
from app.schemas import ContentPage, EventInput
from app.services.catalog import CatalogService

router = APIRouter(prefix='/history', tags=['history'])


@router.post('/events', status_code=202)
def event(data: EventInput, store=Depends(get_store), user=Depends(current_user)):
    if data.event_type in ('content_view', 'recommendation_click', 'recommendation_impression') and not data.content_id:
        raise HTTPException(422, '콘텐츠 식별자가 필요합니다.')
    if data.content_id:
        CatalogService(store).require(data.content_id)
    store.event({'event_id': str(data.event_id), 'event_type': data.event_type, 'user_id': user.id,
                 'content_id': data.content_id, 'properties': {'category': data.category} if data.category else {}})
    return {'accepted': True}


@router.get('', response_model=ContentPage)
def listing(store=Depends(get_store), user=Depends(current_user)):
    items = CatalogService(store).serialize(store.recent(user.id), user)
    return ContentPage(items=items, total=len(items), size=100)
