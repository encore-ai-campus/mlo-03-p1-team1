from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from starlette.concurrency import run_in_threadpool
from app.api.deps import current_user, get_payments, get_store
from app.core.config import get_settings
from app.schemas import CancelInput, OrderInput, OrderOut

router = APIRouter(prefix='/payments', tags=['payments'])


@router.get('/config')
def config(settings=Depends(get_settings)):
    return {'enabled': bool(settings.payment_ready), 'refunds_enabled': settings.refunds_enabled,
            'store_id': settings.portone_store_id, 'channel_key': settings.portone_channel_key}


@router.post('/orders', response_model=OrderOut, status_code=201)
def create(data: OrderInput, idempotency_key: UUID = Header(), user=Depends(current_user), service=Depends(get_payments)):
    return service.create_order(user, data, idempotency_key)


@router.post('/webhook')
async def webhook(request: Request, service=Depends(get_payments)):
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 65536:
            raise HTTPException(413, '웹훅 본문이 너무 큽니다.')
    return await run_in_threadpool(service.webhook, bytes(body), dict(request.headers))


@router.get('', response_model=list[OrderOut])
def listing(store=Depends(get_store), user=Depends(current_user)):
    return store.orders(user.id)


@router.post('/{payment_id}/verify', response_model=OrderOut)
def verify(payment_id: str, user=Depends(current_user), service=Depends(get_payments)):
    return service.verify(payment_id, user)


@router.post('/{payment_id}/cancel', response_model=OrderOut)
def cancel(payment_id: str, data: CancelInput, user=Depends(current_user), service=Depends(get_payments)):
    return service.cancel(payment_id, user, data.reason)
