from fastapi import APIRouter
from app.api.v1 import admin, auth, bookmarks, contents, history, payments, recommendations, reservations, reviews, surveys, users, visits

router = APIRouter(prefix='/api/v1')
for module in (auth, users, surveys, contents, reviews, bookmarks, recommendations, history, payments, reservations, visits, admin):
    router.include_router(module.router)
