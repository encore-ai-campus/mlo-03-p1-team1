"""Idempotent fictional catalogue for local development; never creates a user."""
from datetime import timedelta

from app.core.security import seoul_today
from app.db.session import SessionLocal
from app.models import Content
from app.repositories.store import Store

SAMPLES = [
    ('감각의 조각들', '일상과 예술 사이, 새로운 시선', '전시', '서울', '오디너리 아트스페이스', '서울 종로구 · 가상 전시장', 18000, ['현대미술', '디자인'], 'shapes'),
    ('빛이 머무는 정원', '빛과 색으로 거니는 상상의 풍경', '전시', '서울', '그라운드 갤러리', '서울 성동구 · 가상 전시장', 15000, ['몰입형', '현대미술'], 'garden'),
    ('어쩌면, 해피엔딩', '두 사람의 작고 다정한 이야기', '뮤지컬', '서울', '오디너리 드림씨어터', '서울 중구 · 가상 공연장', 60000, ['이야기', '가족'], 'musical'),
    ('밤의 재즈, 서울', '도시의 밤을 채우는 따뜻한 리듬', '음악', '서울', '블루노트 스테이지', '서울 마포구 · 가상 공연장', 35000, ['재즈', '인디'], 'jazz'),
    ('사적인 풍경', '렌즈 너머로 바라본 우리의 일상', '전시', '부산', '바다사진미술관', '부산 해운대구 · 가상 미술관', 0, ['사진', '야외'], 'photo'),
    ('작은 별의 여행', '상상하는 마음을 위한 한 편의 무대', '연극', '서울', '대학로 소극장 별', '서울 종로구 · 가상 극장', 30000, ['이야기', '가족'], 'theatre'),
    ('몸의 언어', '움직임으로 전하는 말 없는 이야기', '무용', '경기', '수원 컨템포러리홀', '경기 수원시 · 가상 공연장', 25000, ['현대미술', '이야기'], 'dance'),
    ('가을, 공원에서', '음악과 산책이 함께하는 주말', '축제', '서울', '오디너리 시민공원', '서울 영등포구 · 가상 공원', 0, ['야외', '인디'], 'festival'),
    ('선과 면의 대화', '디자인으로 읽는 오늘의 감각', '전시', '경기', '판교 디자인랩', '경기 성남시 · 가상 전시장', 12000, ['디자인', '현대미술'], 'shapes'),
    ('오후의 클래식', '잠시 멈춰 듣는 현악의 선율', '음악', '대전', '오디너리 체임버홀', '대전 서구 · 가상 공연장', 20000, ['클래식', '가족'], 'garden'),
    ('우리가 만난 계절', '다시 꺼내 보는 청춘의 한 페이지', '연극', '부산', '부산 작은무대', '부산 수영구 · 가상 극장', 22000, ['이야기', '인디'], 'theatre'),
    ('종이의 숲', '손끝에서 시작되는 작은 세상', '전시', '제주', '제주 아틀리에 숲', '제주 제주시 · 가상 전시장', 0, ['디자인', '가족'], 'festival'),
]


def seed():
    count = 0
    with SessionLocal.begin() as db:
        store = Store(db)
        for index, (title, subtitle, category, region, venue, address, price, tags, poster) in enumerate(SAMPLES):
            if store.source_content('sample', str(index + 1)):
                continue
            store.add(Content(source='sample', source_id=str(index + 1), title=title, subtitle=subtitle,
                              category=category, region=region, venue=venue, address=address,
                              start_date=seoul_today() - timedelta(days=7) + timedelta(days=index),
                              end_date=seoul_today() + timedelta(days=30 + index * 3), price=price,
                              price_text=f'{price:,}원' if price else '무료',
                              description=f'{subtitle}.\n\n{title}에서 당신의 일상에 새로운 감각을 더해 보세요. {", ".join(tags)}에 관심 있는 분들을 위한 문화 경험입니다.\n\n이 정보는 Oddinary의 검색·찜·리뷰·추천 기능을 체험하기 위한 가상 행사입니다. 실제 개최 정보가 아니며 예매 및 결제는 지원하지 않습니다.',
                              image_url=f'/posters/{poster}.svg', tags=tags, is_sample=True, bookable=False))
            count += 1
    print(f'Added {count} sample contents (no real events or purchases).')


if __name__ == '__main__':
    seed()
