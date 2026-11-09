import logging
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.router import router
from app.core.config import get_settings
from app.db.session import engine
from app.db.mongo import close_mongo
from app.services.events import event_delivery_loop

settings = get_settings()


@asynccontextmanager
async def lifespan(app):
    stop = asyncio.Event()
    task = None
    if settings.mongodb_events_enabled and settings.mongodb_url.get_secret_value():
        task = asyncio.create_task(event_delivery_loop(stop))
    try:
        yield
    finally:
        stop.set()
        if task:
            await task
        close_mongo()


app = FastAPI(title='CulturePick API', version='1.0.0', description='문화 콘텐츠 탐색과 취향·행동 기반 추천', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                   allow_methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
                   allow_headers=['Authorization', 'Content-Type', 'Idempotency-Key',
                                  'X-Activity-Anonymous-Id', 'X-Activity-Session-Id', 'X-Activity-Page'])
app.include_router(router)


@app.exception_handler(SQLAlchemyError)
async def database_error(request: Request, exc: SQLAlchemyError):
    # Do not log driver messages: DSNs/SQL parameters may contain credentials or user data.
    logging.getLogger('culturepick').error('Database operation failed (%s)', type(exc).__name__)
    return JSONResponse(status_code=503, content={'detail': 'DB 연결 또는 스키마를 확인해 주세요. 설정 안내는 docs/setup.md에 있습니다.'})


@app.middleware('http')
async def headers(request: Request, call_next):
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Cache-Control'] = 'no-store'
    return response


@app.get('/api/v1/health', tags=['health'])
def health():
    return {'status': 'ok'}


@app.get('/api/v1/ready', tags=['health'])
def ready():
    with engine.connect() as connection:
        connection.execute(text('SELECT 1'))
    return {'status': 'ready', 'database': 'mariadb'}
