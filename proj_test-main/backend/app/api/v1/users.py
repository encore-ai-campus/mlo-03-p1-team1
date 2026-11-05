from fastapi import APIRouter, Depends
from sqlalchemy import select
from app.api.deps import current_user, get_store
from app.models import Review, Content
from app.schemas import ProfileInput, UserOut, UserReviewOut

router = APIRouter(prefix='/users', tags=['users'])


@router.get('/me', response_model=UserOut)
def me(user=Depends(current_user)):
    return user


@router.patch('/me', response_model=UserOut)
def update(data: ProfileInput, user=Depends(current_user)):
    user.name = data.name
    return user


@router.get('/me/reviews', response_model=list[UserReviewOut])
def my_reviews(store=Depends(get_store), user=Depends(current_user)):
    rows = store.db.execute(select(Review, Content.title).join(Content).where(
        Review.user_id == user.id).order_by(Review.updated_at.desc()).limit(100)).all()
    return [UserReviewOut(id=r.id, user_id=user.id, name=user.name, rating=r.rating,
        body=r.body, updated_at=r.updated_at, content_id=r.content_id, content_title=title) for r, title in rows]
