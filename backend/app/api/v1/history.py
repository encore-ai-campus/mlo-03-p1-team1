from fastapi import APIRouter, Depends, HTTPException
from app.api.deps import current_user, get_store, optional_user
from app.schemas import ContentPage, EventInput
from app.services.catalog import CatalogService

router = APIRouter(prefix='/history', tags=['history'])


@router.post('/events', status_code=202)
def event(data: EventInput, store=Depends(get_store), user=Depends(optional_user)):
    if user is None and (data.anonymous_id is None or data.session_id is None):
        raise HTTPException(422, '비로그인 이벤트에는 익명 ID와 세션 ID가 필요합니다.')
    if data.content_id:
        CatalogService(store).require(data.content_id)
    properties = {key: getattr(data, key) for key in ('category', 'query_length', 'filter_name', 'filter_value')
                  if getattr(data, key) is not None}
    context = {key: str(getattr(data, key)) for key in ('anonymous_id', 'session_id', 'page_path', 'referrer_path')
               if getattr(data, key) is not None}
    if context:
        properties['_context'] = context
    store.event({'event_id': str(data.event_id), 'event_type': data.event_type, 'user_id': user.id if user else None,
                 'content_id': data.content_id, 'properties': properties})
    return {'accepted': True}


@router.get('', response_model=ContentPage)
def listing(store=Depends(get_store), user=Depends(current_user)):
    items = CatalogService(store).serialize(store.recent(user.id), user)
    return ContentPage(items=items, total=len(items), size=100)
