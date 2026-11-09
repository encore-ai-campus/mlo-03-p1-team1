import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.router import router
from app.core.config import get_settings
from app.db.session import engine

settings = get_settings()
app = FastAPI(title='CulturePick API', version='1.0.0', description='문화 콘텐츠 탐색과 취향·행동 기반 추천')
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                   allow_methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
                   allow_headers=['Authorization', 'Content-Type', 'Idempotency-Key'])
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
