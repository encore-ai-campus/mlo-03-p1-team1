from fastapi import APIRouter, Depends
from app.api.deps import current_user, get_store
from app.schemas import ProfileInput, UserOut
from app.services.users import update_profile

router = APIRouter(prefix='/users', tags=['users'])


@router.get('/me', response_model=UserOut)
def me(user=Depends(current_user)):
    return user


@router.patch('/me', response_model=UserOut)
def update(data: ProfileInput, user=Depends(current_user), store=Depends(get_store)):
    return update_profile(store, user, data)
