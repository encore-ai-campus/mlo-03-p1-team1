from fastapi import APIRouter, Depends
from app.api.deps import current_user, get_store

router = APIRouter(prefix='/reservations', tags=['reservations'])


@router.get('')
def listing(store=Depends(get_store), user=Depends(current_user)):
    return [{'id': r.id, 'payment_id': r.payment_id, 'content_id': c.id, 'title': c.title,
             'venue': c.venue, 'start_date': c.start_date, 'status': r.status,
             'quantity': order.quantity, 'amount': order.amount} for r, c, order in store.reservations(user.id)]
