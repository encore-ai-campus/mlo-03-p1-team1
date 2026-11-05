from fastapi import APIRouter, Depends

from app.api.deps import auth_limit, bearer, current_user, get_store
from app.schemas import AuthOut, LoginInput, RegisterInput
from app.services import auth

router = APIRouter(prefix='/auth', tags=['auth'])


@router.post('/register', response_model=AuthOut, status_code=201, dependencies=[Depends(auth_limit)])
def register(data: RegisterInput, store=Depends(get_store)):
    return auth.register(store, data)


@router.post('/login', response_model=AuthOut, dependencies=[Depends(auth_limit)])
def login(data: LoginInput, store=Depends(get_store)):
    return auth.login(store, data)


@router.post('/logout', dependencies=[Depends(current_user)])
def logout(credentials=Depends(bearer), store=Depends(get_store)):
    return auth.logout(store, credentials.credentials)
