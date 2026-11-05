from urllib.parse import unquote

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
