"""실제 headless Chromium에서 사이트 UI 구조를 본뜬 격리 페이지로 검증합니다."""
import json
import unittest
from urllib.parse import urlparse

from playwright.async_api import async_playwright

from src.persona_loader import load_persona, load_rules
from src.simulator import ROOT, Simulator


DETAIL = """<!doctype html><html lang="ko"><meta charset="utf-8">
<main><h1>테스트 전시</h1><p>전시</p><p>#공예</p>
<button onclick="document.querySelector('dialog').showModal()">결제하기</button>
<dialog aria-label="결제 확인"><p>실제 금액이 청구되지 않는 체험용 결제입니다.</p>
<button onclick="document.querySelector('dialog').close()">취소</button>
<button onclick="location.href='/mypage/payments'">결제하기</button></dialog>
<form onsubmit="event.preventDefault(); document.getElementById('notice').textContent='리뷰를 저장했어요.';">
<input type="radio" name="rating" aria-label="3점">
<input type="radio" name="rating" aria-label="4점">
<input type="radio" name="rating" aria-label="5점">
<label for="review-body">감상 리뷰</label><textarea id="review-body" required minlength="5"></textarea>
<button>리뷰 저장</button></form><div id="notice" role="status"></div></main></html>"""


class BrowserActionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.playwright = await async_playwright().start()
        try:
            self.browser = await self.playwright.chromium.launch(headless=True)
        except Exception as exc:
            await self.playwright.stop()
            self.skipTest(f"Chromium 실행 환경 필요: {exc}")
        self.page = await self.browser.new_page()
        self.page.set_default_timeout(2000)
        self.requests = []

        async def route(request):
            path = urlparse(request.request.url).path
            self.requests.append(path)
            if path == "/contents/1":
                html = DETAIL
            elif path == "/recommendations":
                html = '<main><a href="/contents/1">추천 전시 상세 보기</a></main>'
            elif path == "/mypage/payments":
                html = '<main><h1>결제 내역</h1></main>'
            else:
                html = '<header><a href="/recommendations">취향 추천</a></header><main>홈</main>'
            await request.fulfill(status=200, content_type="text/html; charset=utf-8", body=html)

        await self.page.route("**/*", route)
        rules = load_rules()
        persona = load_persona("persona_001.md", rules)
        probabilities = json.loads((ROOT / "runs/persona_001_behavior.json").read_text(encoding="utf-8"))
        self.sim = Simulator(persona, rules, probabilities)

    async def asyncTearDown(self):
        if hasattr(self, "browser"):
            await self.browser.close()
            await self.playwright.stop()

    async def test_recommendation_list_and_actual_link_click_to_detail(self):
        await self.page.goto("https://oddinary.test/")
        await self.sim._recommendation(self.page, self.page.get_by_role("link", name="취향 추천"))
        self.assertEqual(self.requests, ["/", "/recommendations", "/contents/1"])
        self.assertEqual(self.sim.viewed[0]["content_id"], "1")
        self.assertEqual(self.sim.viewed[0]["source"], "취향 기반 추천")
        self.assertEqual(self.sim.viewed[0]["tags"], ["공예"])

    async def test_virtual_checkout_finishes_on_payment_history(self):
        await self.page.goto("https://oddinary.test/contents/1")
        button = self.page.get_by_role("button", name="결제하기", exact=True)
        await self.sim._purchase(self.page, button, "1")
        self.assertEqual(urlparse(self.page.url).path, "/mypage/payments")
        self.assertIn("1", self.sim.purchased)
        self.assertIn("1", self.sim.purchase_attempts)

    async def test_checkout_without_virtual_payment_notice_is_not_submitted(self):
        await self.page.goto("https://oddinary.test/contents/1")
        await self.page.locator("dialog p").evaluate("e => e.textContent = '일반 결제'")
        await self.sim._purchase(self.page, self.page.get_by_role("button", name="결제하기", exact=True), "1")
        self.assertEqual(self.requests, ["/contents/1"])
        self.assertFalse(self.sim.purchased)
        self.assertFalse(await self.page.get_by_role("dialog").is_visible())

    async def test_review_selects_rating_and_waits_for_save_confirmation(self):
        await self.page.goto("https://oddinary.test/contents/1")
        box = self.page.get_by_role("textbox", name="감상 리뷰", exact=True)
        await self.sim._review(self.page, box, "1")
        self.assertIn("[시뮬레이션 리뷰]", await box.input_value())
        self.assertEqual(await self.page.locator('input[type="radio"]:checked').count(), 1)
        self.assertIn("1", self.sim.reviewed)


if __name__ == "__main__":
    unittest.main()
