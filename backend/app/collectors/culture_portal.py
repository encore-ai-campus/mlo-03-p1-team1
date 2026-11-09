from urllib.parse import unquote
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import time

from defusedxml import ElementTree
import httpx


class CollectionError(Exception):
    pass


class CulturePortal:
    def __init__(self, settings):
        self.settings = settings

    def request(self, client, path, params):
        try:
            response = client.get(path, params={'serviceKey': unquote(self.settings.culture_api_key), **params})
            response.raise_for_status()
            if len(response.content) > 5_000_000:
                raise ValueError('Payload too large')
            root = ElementTree.fromstring(response.content)
            code = root.findtext('.//resultCode') or root.findtext('.//returnReasonCode')
            if code and code not in ('00', '0000', '0'):
                raise ValueError('Provider rejected request')
            if root.find('.//OpenAPI_ServiceResponse') is not None or root.tag == 'OpenAPI_ServiceResponse':
                raise ValueError('Invalid service key or provider response')
            return root
        except Exception:
            # Never include request URLs: they contain the API key.
            raise CollectionError('문화포털 수집 실패: API 키·활용 승인·공급자 응답을 확인하세요.') from None

    def collect(self, start, end, max_pages=5):
        if not self.settings.culture_api_key:
            raise CollectionError('CULTURE_API_KEY 설정이 필요합니다.')
        with httpx.Client(base_url=self.settings.culture_api_base_url.rstrip('/') + '/', timeout=20, follow_redirects=False) as client:
            for page in range(1, max_pages + 1):
                root = self.request(client, 'period', {'from': start.strftime('%Y%m%d'), 'to': end.strftime('%Y%m%d'), 'cPage': page, 'rows': 100, 'sortStdr': 1})
                nodes = root.findall('.//perforList')
                if not nodes:
                    break
                for node in nodes:
                    data = {c.tag: c.text or '' for c in node}
                    seq = data.get('seq', '').strip()
                    if not seq:
                        continue
                    detail = self.request(client, 'detail', {'seq': seq})
                    info = detail.find('.//perforInfo')
                    if info is not None:
                        data.update({c.tag: c.text or '' for c in info})
                    yield data
                if len(nodes) < 100:
                    break


class KcisaCulturePortal:
    """Culture Portal dataset 580: CNV_060 JSON list API, not the legacy period/detail API."""

    URL = 'https://api.kcisa.kr/openapi/CNV_060/request'
    GENRES = ('연극', '뮤지컬', '오페라', '음악', '콘서트', '국악', '무용', '전시', '기타')

    def __init__(self, settings):
        self.settings = settings

    def page(self, client, genre, number, rows=1000):
        for attempt in range(3):
            try:
                response = client.get(self.URL, params={
                    'serviceKey': unquote(self.settings.culture_api_key), 'numOfRows': rows,
                    'pageNo': number, 'dtype': genre, 'title': '',
                }, headers={'Accept': 'application/json'})
                response.raise_for_status()
                if len(response.content) > 20_000_000:
                    raise ValueError('Payload too large')
                data = response.json()['response']
                if data['header']['resultCode'] != '0000':
                    raise ValueError('Provider rejected request')
                body = data['body']
                items = (body.get('items') or {}).get('item') or []
                if isinstance(items, dict):
                    items = [items]
                if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
                    raise ValueError('Invalid item list')
                return items, int(body.get('totalCount') or 0)
            except Exception:
                if attempt < 2:
                    time.sleep(attempt + 1)
        # Deliberately omit driver errors and URLs containing serviceKey.
        raise CollectionError(f'KCISA 수집 실패: 분야 {genre}, 페이지 {number}. 기존 DB는 유지됩니다.')

    def collect(self, progress=None):
        if not self.settings.culture_api_key:
            raise CollectionError('CULTURE_API_KEY 설정이 필요합니다.')

        def category(genre):
            result, seen_pages = [], set()
            with httpx.Client(timeout=40, follow_redirects=False) as client:
                for number in range(1, 1001):
                    items, total = self.page(client, genre, number)
                    fingerprint = hashlib.sha256(json.dumps(items, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
                    if items and fingerprint in seen_pages:
                        raise CollectionError('공급자가 이전 페이지를 반복 반환했습니다. 기존 DB는 유지됩니다.')
                    seen_pages.add(fingerprint)
                    result.extend({**item, '_dtype': genre} for item in items)
                    if progress:
                        progress(genre, number, len(result), total)
                    # totalCount is global even with dtype applied. Stop on actual page size.
                    if len(items) < 1000:
                        return result
            raise CollectionError('수집 페이지 상한에 도달했습니다. 기존 DB는 유지됩니다.')

        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = [pool.submit(category, genre) for genre in self.GENRES]
            for future in as_completed(futures):
                yield from future.result()
