from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from app.api.deps import get_store, optional_user
from app.schemas import Category, ContentOut, ContentPage
from app.services.catalog import CatalogService

router = APIRouter(prefix='/contents', tags=['contents'])


@router.get('', response_model=ContentPage)
def listing(q: str = Query('', max_length=100), category: Category | None = None,
            region: str | None = Query(None, max_length=30), free_only: bool = False,
            from_date: date | None = None, to_date: date | None = None, include_ended: bool = False,
            sort: Literal['latest', 'popular', 'ending'] = 'latest',
            page: int = Query(1, ge=1, le=1000), size: int = Query(24, ge=1, le=48),
            store=Depends(get_store), user=Depends(optional_user)):
    if from_date and to_date and from_date > to_date:
        raise HTTPException(422, '종료일은 시작일 이후여야 합니다.')
    items, total = store.contents(q=q, category=category, region=region, free_only=free_only,
                                  from_date=from_date, to_date=to_date, include_ended=include_ended,
                                  sort=sort, page=page, size=size)
    return ContentPage(items=CatalogService(store).serialize(items, user), total=total, page=page, size=size)


@router.get('/{content_id}', response_model=ContentOut)
def detail(content_id: int, store=Depends(get_store), user=Depends(optional_user)):
    service = CatalogService(store)
    return service.serialize([service.require(content_id)], user)[0]
