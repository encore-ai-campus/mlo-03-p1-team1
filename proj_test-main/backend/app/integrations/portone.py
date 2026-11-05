from urllib.parse import quote

import httpx
from fastapi import HTTPException
from standardwebhooks.webhooks import EmptyWebhookSecretError, Webhook, WebhookVerificationError


class PortOne:
    def __init__(self, settings):
        self.settings = settings

    def request(self, method, path, **kwargs):
        try:
            with httpx.Client(timeout=12, base_url=self.settings.portone_api_base_url) as client:
                response = client.request(method, path, headers={'Authorization': f'PortOne {self.settings.portone_api_secret}'}, **kwargs)
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise ValueError('Invalid response')
                return payload
        except (httpx.HTTPError, ValueError):
            raise HTTPException(502, '결제사 응답을 확인할 수 없습니다. 결제 내역에서 다시 확인해 주세요.')

    def get_payment(self, payment_id):
        return self.request('GET', f'/payments/{quote(payment_id, safe="")}', params={'storeId': self.settings.portone_store_id})

    def cancel_payment(self, payment_id, amount, reason):
        return self.request('POST', f'/payments/{quote(payment_id, safe="")}/cancel', json={
            'storeId': self.settings.portone_store_id, 'amount': amount,
            'currentCancellableAmount': amount, 'reason': reason, 'requester': 'CUSTOMER'})

    def verify_webhook(self, body: bytes, headers: dict):
        if not self.settings.portone_webhook_secret:
            raise HTTPException(503, '웹훅 검증 설정이 필요합니다.')
        try:
            return Webhook(self.settings.portone_webhook_secret).verify(body, headers)
        except (WebhookVerificationError, ValueError, EmptyWebhookSecretError):
            raise HTTPException(400, '웹훅 서명을 확인할 수 없습니다.')
