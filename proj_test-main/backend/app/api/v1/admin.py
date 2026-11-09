from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from app.api.deps import current_user, get_store
from app.models import BehaviorEvent, Bookmark, CollectionRun, Content, Review, User

router = APIRouter(prefix='/admin', tags=['admin'])


def administrator(user=Depends(current_user)):
    if not user.is_admin:
        raise HTTPException(403, '관리자만 접근할 수 있습니다.')
    return user


@router.get('/overview')
def overview(store=Depends(get_store), user=Depends(administrator)):
    db = store.db
    counts = {key: db.scalar(select(func.count()).select_from(model)) for key, model in (
        ('contents', Content), ('members', User), ('bookmarks', Bookmark), ('reviews', Review), ('events', BehaviorEvent))}
    categories = [{'name': name, 'count': count} for name, count in db.execute(
        select(Content.category, func.count()).group_by(Content.category)).all()]
    activities = [{'name': name, 'count': count} for name, count in db.execute(
        select(BehaviorEvent.event_type, func.count()).group_by(BehaviorEvent.event_type)).all()]
    runs = list(db.scalars(select(CollectionRun).order_by(CollectionRun.started_at.desc()).limit(20)))
    return {'counts': counts, 'categories': categories, 'activities': activities, 'runs': [
        {'id': r.id, 'started_at': r.started_at.isoformat() + 'Z',
         'finished_at': r.finished_at.isoformat() + 'Z' if r.finished_at else None,
         'status': r.status, 'collected_count': r.collected_count, 'error_code': r.error_code} for r in runs]}
