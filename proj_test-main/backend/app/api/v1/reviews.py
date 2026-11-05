from fastapi import APIRouter, Depends
from app.api.deps import current_user, get_store
from app.schemas import ReviewInput, ReviewOut
from app.services.catalog import CatalogService

router = APIRouter(prefix='/contents', tags=['reviews'])


@router.get('/{content_id}/reviews', response_model=list[ReviewOut])
def listing(content_id: int, store=Depends(get_store)):
    CatalogService(store).require(content_id)
    return [ReviewOut(id=r.id, user_id=r.user_id, name=name, rating=r.rating, body=r.body, updated_at=r.updated_at)
            for r, name in store.reviews(content_id)]


@router.put('/{content_id}/reviews/me', response_model=ReviewOut)
def save(content_id: int, data: ReviewInput, store=Depends(get_store), user=Depends(current_user)):
    return CatalogService(store).save_review(user, content_id, data)


@router.delete('/{content_id}/reviews/me')
def remove(content_id: int, store=Depends(get_store), user=Depends(current_user)):
    return CatalogService(store).delete_review(user, content_id)
