from datetime import timedelta
import secrets

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.core.security import password_hash, password_matches, token_hash, utcnow
from app.models import AuthSession, User
from app.schemas import AuthOut, UserOut


def create_session(store, user):
    token = secrets.token_urlsafe(40)
    store.add(AuthSession(token_hash=token_hash(token), user_id=user.id, expires_at=utcnow() + timedelta(days=7)))
    return AuthOut(access_token=token, user=UserOut.model_validate(user))


def register(store, data):
    email = str(data.email).lower()
    if store.user_by_email(email):
        raise HTTPException(409, '이미 가입된 이메일입니다.')
    values = data.model_dump(exclude={'email', 'password', 'survey'}, exclude_unset=True)
    if data.age is not None:
        values['age_recorded_at'] = utcnow().replace(microsecond=0)
    if data.survey is not None:
        values.update(categories=list(dict.fromkeys(data.survey.categories)), tags=data.survey.tags,
                      survey_completed=True)
    try:
        user = store.add(User(email=email, password_hash=password_hash(data.password), **values))
    except IntegrityError:
        store.rollback()
        raise HTTPException(409, '이미 가입된 이메일입니다.')
    return create_session(store, user)


def login(store, data):
    user = store.user_by_email(str(data.email).lower())
    # A dummy hash keeps missing-account timing close to incorrect-password timing.
    encoded = user.password_hash if user else 'scrypt$00000000000000000000000000000000$' + '0' * 128
    if not password_matches(data.password, encoded) or user is None:
        raise HTTPException(401, '이메일 또는 비밀번호를 확인해 주세요.')
    return create_session(store, user)


def logout(store, token):
    store.delete(store.session(token_hash(token)))
    return {'ok': True}
