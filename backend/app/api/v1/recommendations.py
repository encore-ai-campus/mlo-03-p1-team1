from fastapi import APIRouter, Depends, Query
from app.api.deps import get_store, optional_user
from app.schemas import ContentPage
from app.services.catalog import CatalogService

router = APIRouter(prefix='/recommendations', tags=['recommendations'])


@router.get('', response_model=ContentPage)
def listing(size: int = Query(8, ge=1, le=24), store=Depends(get_store), user=Depends(optional_user)):
    items = CatalogService(store).recommendations(user, size)
    return ContentPage(items=items, total=len(items), size=size)
