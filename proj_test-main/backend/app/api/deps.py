from collections import defaultdict, deque
from threading import Lock
import time

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.core.security import token_hash, utcnow
from app.db.session import get_db
from app.integrations.portone import PortOne
from app.repositories.store import Store
from app.services.payments import PaymentService

bearer = HTTPBearer(auto_error=False)


def get_store(db=Depends(get_db, scope='function')):
    return Store(db)


def optional_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), store=Depends(get_store)):
    if not credentials:
        return None
    session = store.session(token_hash(credentials.credentials))
    if session is None or session.expires_at <= utcnow():
        raise HTTPException(401, '로그인이 만료되었습니다. 다시 로그인해 주세요.')
    return store.user(session.user_id)


def current_user(user=Depends(optional_user)):
    if user is None:
        raise HTTPException(401, '로그인이 필요합니다.')
    return user


def get_payments(store=Depends(get_store), settings=Depends(get_settings)):
    return PaymentService(store, settings, PortOne(settings))


_attempts = defaultdict(deque)
_lock = Lock()


def auth_limit(request: Request):
    host = request.client.host if request.client else 'unknown'
    now = time.monotonic()
    with _lock:
        # Prune abandoned keys as well, keeping the in-process limiter bounded.
        for key in list(_attempts):
            if not _attempts[key] or _attempts[key][-1] < now - 60:
                del _attempts[key]
        attempts = _attempts[host]
        while attempts and attempts[0] < now - 60:
            attempts.popleft()
        if len(attempts) >= 20:
            raise HTTPException(429, '잠시 후 다시 시도해 주세요.', headers={'Retry-After': '60'})
        attempts.append(now)
