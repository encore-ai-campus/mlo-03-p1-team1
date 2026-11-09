from datetime import datetime
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urlparse


class TextOnly(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def text(value: str, length: int) -> str:
    parser = TextOnly()
    parser.feed(unescape(value or ''))
    return ' '.join(' '.join(parser.parts).split())[:length]


def safe_url(value: str) -> str:
    value = (value or '').strip()
    return value[:1000] if urlparse(value).scheme in ('http', 'https') else ''


def normalize(data: dict) -> dict:
    title = text(data.get('title', ''), 300)
    source_id = data.get('seq', '').strip()
    if not title or not source_id or len(source_id) > 100:
        raise ValueError('Missing source id or title')
    def parse_date(value):
        return datetime.strptime(value.replace('-', '').replace('.', '').strip(), '%Y%m%d').date()
    start, end = parse_date(data.get('startDate', '')), parse_date(data.get('endDate', ''))
    if end < start:
        raise ValueError('Reversed event date range')
    realm = text(data.get('realmName', ''), 30)
    category = '전시' if any(k in realm for k in ('미술', '전시')) else next((c for c in ['뮤지컬', '연극', '무용', '축제', '음악'] if c in realm), '음악' if '국악' in realm else '축제')
    region = text(data.get('area', ''), 30)
    for full, short in [('서울', '서울'), ('경기도', '경기'), ('강원', '강원'), ('충청북', '충북'), ('충청남', '충남'), ('전라북', '전북'), ('전라남', '전남'), ('경상북', '경북'), ('경상남', '경남'), ('제주', '제주')]:
        if region.startswith(full):
            region = short
            break
    region = region.replace('광역시', '').replace('특별시', '').replace('특별자치시', '')
    price_text = text(data.get('price', ''), 200)
    # Provider price may contain tiers/discounts. Do not infer a sellable ticket price.
    free = price_text.strip() in ('무료', '전석 무료', '전석무료', '0원')
    return dict(source='culture_portal', source_id=source_id, title=title, subtitle='', category=category,
                region=region, venue=text(data.get('place', ''), 200), address=text(data.get('placeAddr', ''), 400),
                start_date=start, end_date=end, price=0, price_text='무료' if free else price_text or '주최 기관 확인',
                description=text(data.get('contents1', '') or data.get('contents', ''), 20000) or '상세 정보는 공식 홈페이지에서 확인해 주세요.',
                image_url=safe_url(data.get('imgUrl', '') or data.get('thumbnail', '')),
                source_url=safe_url(data.get('url', '')), tags=[category], is_sample=False, bookable=False)
