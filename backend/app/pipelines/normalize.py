from datetime import date, datetime, timedelta
import hashlib
import re
from html import unescape
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlparse


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


KCISA_REGIONS = ('서울', '부산', '대구', '인천', '광주', '대전', '울산', '세종', '경기',
                 '강원', '충북', '충남', '전북', '전남', '경북', '경남', '제주')
KCISA_PRICES = (0, 3000, 5000, 8000, 10000, 12000, 15000, 18000, 20000,
                25000, 30000, 35000, 45000, 55000, 70000, 90000, 120000)
KCISA_CATEGORIES = {'연극': '연극', '뮤지컬': '뮤지컬', '오페라': '음악', '음악': '음악',
                    '콘서트': '음악', '국악': '음악', '무용': '무용', '전시': '전시', '기타': '축제'}


def normalize_kcisa(data: dict, today: date, demo_attributes: bool = False) -> tuple[dict, dict]:
    """Map dataset 580 fields; keep a separate audit of every synthetic attribute."""
    def plain(value, length):
        return ' '.join(unescape(str(value or '')).split())[:length]

    title, venue = plain(data.get('title'), 300), plain(data.get('eventSite'), 200)
    if not title:
        raise ValueError('missing_title')
    source_url = safe_url(data.get('url') or '')
    seq = parse_qs(urlparse(source_url).query).get('pSeq', [''])[0]
    if not seq or len(seq) > 100:
        identity = '|'.join((title, venue, str(data.get('eventPeriod') or data.get('period') or '')))
        seq = hashlib.sha256(identity.encode('utf-8')).hexdigest()
    raw_period = plain(data.get('period') or data.get('eventPeriod'), 500)
    matches = re.findall(r'(?<!\d)(\d{4})[-./]?\s*(\d{2})[-./]?\s*(\d{2})(?!\d)', raw_period)
    if not matches:
        raise ValueError('missing_dates')
    try:
        start = date(*(int(part) for part in matches[0]))
        end = date(*(int(part) for part in matches[-1]))
    except ValueError as exc:
        raise ValueError('invalid_dates') from exc
    if end < start or start.year < 1000:
        raise ValueError('invalid_date_range')
    audit = {'source_id': seq, 'original_period': raw_period, 'date_adjusted': False}
    if start.year <= 9994:
        try:
            anniversary = start.replace(year=start.year + 5)
        except ValueError:
            anniversary = start.replace(year=start.year + 5, day=28)
        if end >= anniversary:
            audit.update(original_start=start.isoformat(), original_end=end.isoformat(), date_adjusted=True)
            if end < today:
                start = max(start, end - timedelta(days=180))
            elif start > today:
                end = min(end, start + timedelta(days=180))
            else:
                start, end = max(start, today - timedelta(days=30)), min(end, today + timedelta(days=180))
            audit.update(adjusted_start=start.isoformat(), adjusted_end=end.isoformat())
    genre = plain(data.get('_dtype') or data.get('type') or '기타', 30)
    category = KCISA_CATEGORIES.get(genre, '축제')
    raw_charge = plain(data.get('charge'), 200)
    region, price = '지역 확인 필요', 0
    price_text = '무료' if raw_charge in ('무료', '전석무료', '전석 무료', '0원') else raw_charge or '주최 기관 확인'
    description = text(data.get('description') or '', 18000)
    subtitle = ''
    if demo_attributes:
        digest = int(hashlib.sha256((seq + '|demo-v1').encode()).hexdigest(), 16)
        region = KCISA_REGIONS[digest % len(KCISA_REGIONS)]
        price = KCISA_PRICES[(digest // len(KCISA_REGIONS)) % len(KCISA_PRICES)]
        price_text = f'{price:,}원 (테스트)' if price else '무료'
        subtitle = '지역·관람료 필터 테스트 데이터'
        description = ('[테스트용 보정 데이터] 제목·장소·이미지는 문화체육관광부 공개 API 정보입니다. '
                       '지역과 관람료는 사용자 요청에 따라 필터 테스트용으로 배정한 값이며 실제 개최 지역·판매 가격과 다를 수 있습니다.\n\n'
                       + description)
        audit.update(demo_attributes=True, assigned_region=region, assigned_price=price,
                     original_charge=raw_charge, original_type=data.get('type'), queried_genre=genre)
    if audit['date_adjusted']:
        description += (f"\n\n[일정 보정] 원본 {audit['original_start']} ~ {audit['original_end']}는 5년 이상 범위여서 "
                        f'{start.isoformat()} ~ {end.isoformat()}로 보정했습니다. 실제 일정은 공식 출처에서 확인해 주세요.')
    description += '\n\n출처: 문화체육관광부_문화예술공연(통합) / 문화공공데이터광장 API 580'
    if source_url:
        description += '\n공식 정보: ' + source_url
    image_url = safe_url(data.get('imageObject') or '')
    if urlparse(image_url).hostname in ('www.culture.go.kr', 'culture.go.kr'):
        image_url = image_url.replace('http://', 'https://', 1)
    values = dict(source='culture_kcisa', source_id=seq, title=title, subtitle=subtitle, category=category,
                  region=region, venue=venue or '장소 확인 필요', address='', start_date=start, end_date=end,
                  price=price, price_text=price_text, description=description[:20000], image_url=image_url,
                  source_url=source_url, tags=list(dict.fromkeys((category, genre))),
                  is_sample=demo_attributes, bookable=False)
    return values, audit
