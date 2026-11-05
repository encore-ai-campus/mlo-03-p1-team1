from fastapi import APIRouter, Depends
from sqlalchemy import delete, select
from sqlalchemy.dialects.mysql import insert
from app.api.deps import current_user, get_store
from app.core.security import utcnow
from app.models import Content, Visit
from app.schemas import ContentPage
from app.services.catalog import CatalogService

router = APIRouter(prefix='/visits', tags=['visits'])


@router.get('', response_model=ContentPage)
def listing(store=Depends(get_store), user=Depends(current_user)):
    contents = list(store.db.scalars(select(Content).join(Visit).where(
        Visit.user_id == user.id).order_by(Visit.visited_at.desc()).limit(100)))
    return ContentPage(items=CatalogService(store).serialize(contents, user), total=len(contents), size=100)


@router.put('/{content_id}')
def save(content_id: int, store=Depends(get_store), user=Depends(current_user)):
    CatalogService(store).require(content_id)
    stmt = insert(Visit).values(user_id=user.id, content_id=content_id, visited_at=utcnow())
    store.db.execute(stmt.on_duplicate_key_update(content_id=stmt.inserted.content_id))
    return {'visited': True}


@router.delete('/{content_id}')
def remove(content_id: int, store=Depends(get_store), user=Depends(current_user)):
    store.db.execute(delete(Visit).where(Visit.user_id == user.id, Visit.content_id == content_id))
    return {'visited': False}
