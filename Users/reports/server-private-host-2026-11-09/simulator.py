"""실제 사이트에서 관찰 가능한 UI만 사용하는 비동기 Playwright 시뮬레이터."""
import asyncio
import json
import os
import random
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import TimeoutError as PlaywrightTimeoutError, async_playwright
from src.test_accounts import get_test_account, mark_registered

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs"


def now():
    return datetime.now(timezone.utc).isoformat()


async def visible(locator):
    try:
        return await locator.count() > 0 and await locator.first.is_visible() and await locator.first.is_enabled()
    except Exception:
        return False


class Simulator:
    def __init__(self, persona, rules, probabilities):
        self.persona, self.rules, self.probabilities = persona, rules, probabilities
        self.profile = persona["signup_profile"]
        self.traits = persona["simulation_traits"]
        self.rng = random.Random(persona["persona_id"])
        self.timing_rng = random.Random()
        self.events, self.viewed = [], []
        self.purchased, self.reviewed, self.favorite_changes = set(), set(), set()
        self.purchase_attempts, self.review_attempts = set(), set()

    def log(self, action, status, detail="", **extra):
        event = {"timestamp": now(), "action": action, "status": status, "detail": detail, **extra}
        self.events.append(event)
        print(f"[{event['timestamp']}] {action}: {status} - {detail}", flush=True)

    async def dismiss_first_visit(self, page):
        dialog = page.get_by_role("dialog", name="나의 취향으로 시작하기")
        try:
            await dialog.wait_for(state="visible", timeout=5000)
        except Exception:
            return
        close = dialog.get_by_role("button", name="닫기", exact=True)
        if not await visible(close):
            raise RuntimeError("첫 방문 취향 창의 닫기 버튼을 찾을 수 없습니다.")
        await close.click()
        await dialog.wait_for(state="hidden")
        self.log("첫 방문 취향 창 닫기", "성공", "회원가입 화면으로 이동하기 위해 초기 팝업을 닫음")

    async def _fill_account_credentials(self, dialog, name):
        account = get_test_account(self.persona["persona_id"])
        email = account["login_id"]
        password = account["password"]
        await dialog.get_by_role("textbox", name="이메일", exact=True).fill(email)
        await dialog.get_by_role("textbox", name="비밀번호", exact=True).fill(password)
        if name:
            name_box = dialog.get_by_role("textbox", name="이름", exact=True)
            if await visible(name_box):
                await name_box.fill(name)
        return email

    async def _fill_visible_profile(self, dialog):
        """Use only labels/options currently rendered by the site's registration form."""
        profile = self.profile
        field_patterns = {
            "gender": re.compile("성별|gender", re.I), "age": re.compile("나이|연령|age", re.I),
            "region": re.compile("거주지|지역|region", re.I), "occupation": re.compile("직업|occupation|직종", re.I),
            "mbti": re.compile("MBTI", re.I),
        }
        display_values = {"gender": {"female": "여성", "male": "남성", "other": "기타", "prefer_not_to_say": "응답하지 않음"}}
        for key, pattern in field_patterns.items():
            field = dialog.get_by_label(pattern).first
            if not await visible(field):
                continue
            value = str(profile[key])
            tag_name = await field.evaluate("e => e.tagName.toLowerCase()")
            input_type = await field.get_attribute("type")
            if tag_name == "select":
                options = await field.locator("option").evaluate_all("els => els.map(e => ({label:e.textContent.trim(), value:e.value}))")
                candidates = [value, display_values.get(key, {}).get(value, value)]
                match = next((option for option in options if option["value"] in candidates or option["label"] in candidates), None)
                if match:
                    await field.select_option(value=match["value"])
                else:
                    raise ValueError(f"가입 화면의 {key} 선택지에 페르소나 값이 없음: {value}")
            elif input_type in {"radio", "checkbox"}:
                label = display_values.get(key, {}).get(value, value)
                choice = dialog.get_by_label(label, exact=True).first
                if await visible(choice):
                    await choice.check()
            else:
                await field.fill(value)

    async def authenticate(self, page):
        """Register the synthetic account, then log in on duplicate-account retries."""
        try:
            login_trigger = page.get_by_role("button", name="로그인", exact=True)
            if not await visible(login_trigger):
                self.log("회원가입/로그인", "건너뜀", "페이지에서 로그인 진입 버튼을 확인할 수 없음")
                return False
            await login_trigger.first.click()
            dialog = page.get_by_role("dialog")
            await dialog.wait_for(state="visible")
            if get_test_account(self.persona["persona_id"]).get("registered"):
                email = await self._fill_account_credentials(dialog, None)
                await dialog.get_by_role("button", name="로그인", exact=True).last.click()
                await dialog.wait_for(state="hidden", timeout=7000)
                if await visible(page.get_by_role("banner").get_by_role("button", name="로그인", exact=True)):
                    self.log("로그인", "실패", "가입된 사용자 이름이 헤더에 표시되지 않음")
                    return False
                self.log("로그인", "성공", f"계정 {email}")
                return True
            signup_tab = dialog.get_by_role("button", name="회원가입", exact=True)
            if await visible(signup_tab):
                await signup_tab.click()
                email = await self._fill_account_credentials(dialog, f"가상 사용자 {self.persona['persona_id'][-3:]}")
                next_button = dialog.get_by_role("button", name="프로필 입력으로", exact=True)
                if await visible(next_button):
                    await next_button.click()
                    await page.wait_for_timeout(250)
                    await self._fill_visible_profile(dialog)
                    next_step = dialog.get_by_role("button", name=re.compile("취향|다음|저장"))
                    if await visible(next_step):
                        await next_step.first.click()
                        await page.wait_for_timeout(250)
                # On the observed registration wizard the third step is taste selection.
                for category in self.profile["cultural_categories"]:
                    button = dialog.get_by_role("button", name=category, exact=True)
                    if await visible(button):
                        await button.click()
                category_next = dialog.get_by_role("button", name="다음으로", exact=True)
                if await visible(category_next):
                    await category_next.click()
                    await page.wait_for_timeout(250)
                for tab_name in ["세부 장르", "분위기·감성", "관람 스타일"]:
                    tab = dialog.get_by_role("tab", name=tab_name, exact=True)
                    if await visible(tab):
                        await tab.click()
                        for tag in self.profile["tags"]:
                            button = dialog.get_by_role("button", name=tag, exact=True)
                            if await visible(button) and await button.get_attribute("aria-pressed") != "true":
                                await button.click()
                # Require an explicit runtime acknowledgement before accepting legal terms.
                terms = dialog.get_by_role("checkbox", name=re.compile("약관|이용|개인정보|동의"))
                if await visible(terms):
                    if self.rules["session"].get("unattended"):
                        self.log("회원가입", "실패", "약관 동의 확인이 필요한 계정입니다. 단일 실행으로 먼저 가입하세요.")
                        return False
                    print("가입 화면에 약관 동의가 있습니다. 최종 제출 전 사용자 확인이 필요합니다.", flush=True)
                    approved = await asyncio.to_thread(input, "테스트 계정 약관에 동의하고 가입할까요? [y/N] ")
                    if approved.strip().lower() not in {"y", "yes"}:
                        self.log("회원가입", "건너뜀", "실행자가 약관 동의를 승인하지 않음")
                        return False
                    await terms.check()
                submit = dialog.get_by_role("button", name=re.compile("가입하기|가입 완료|취향 저장하기|계정 만들기"))
                if not await visible(submit):
                    self.log("회원가입", "실패", "실제 가입 제출 버튼을 현재 화면에서 확인하지 못함")
                    return False
                await submit.first.click()
                try:
                    await dialog.wait_for(state="hidden", timeout=15000)
                except PlaywrightTimeoutError:
                    errors = (await dialog.inner_text())[-500:]
                    if re.search("이미|중복|사용 중", errors):
                        await dialog.get_by_role("button", name="로그인", exact=True).click()
                        await self._fill_account_credentials(dialog, None)
                        await dialog.get_by_role("button", name="로그인", exact=True).last.click()
                        await dialog.wait_for(state="hidden", timeout=7000)
                    else:
                        self.log("회원가입", "실패", errors)
                        return False
                if await visible(page.get_by_role("banner").get_by_role("button", name="로그인", exact=True)):
                    self.log("회원가입/로그인", "실패", "인증 후 헤더가 로그인 상태로 변경되지 않음")
                    return False
                mark_registered(self.persona["persona_id"])
                self.log("회원가입 및 로그인", "성공", f"계정 {email}; 비밀번호는 결과에 기록하지 않음")
                return True
            # If the modal starts on login, use the dedicated synthetic credentials.
            email = await self._fill_account_credentials(dialog, None)
            await dialog.get_by_role("button", name="로그인", exact=True).last.click()
            await page.wait_for_timeout(800)
            if await dialog.is_visible():
                self.log("로그인", "실패", (await dialog.inner_text())[-400:])
                return False
            self.log("로그인", "성공", f"계정 {email}")
            return True
        except Exception as exc:
            self.log("회원가입/로그인", "실패", str(exc)[:500])
            return False

    async def _open_content(self, page, source="일반 탐색"):
        links = page.locator('main a[href*="/contents/"]')
        await links.first.wait_for(state="visible")
        choices = {}
        for index in range(min(await links.count(), 40)):
            link = links.nth(index)
            href = await link.get_attribute("href")
            if href and re.search(r"/contents/\d+$", href) and await link.is_visible():
                choices.setdefault(href, link)
        if not choices:
            self.log("행사 상세 조회", "건너뜀", "실제 콘텐츠 링크가 없음", source=source)
            return
        seen = {item["content_id"] for item in self.viewed}
        fresh = [href for href in choices if href.rsplit("/", 1)[-1] not in seen]
        href = self.rng.choice(fresh or list(choices))
        await choices[href].click()
        await page.wait_for_url(re.compile(r"/contents/\d+$"))
        await page.locator("main h1").wait_for(state="visible")
        body = await page.locator("main").inner_text()
        content_id = re.search(r"/contents/(\d+)", urlparse(page.url).path).group(1)
        category = next((c for c in self.rules["cultural_categories"] if re.search(rf"(?<!\S){re.escape(c)}(?!\S)", body)), None)
        tags = [tag for group in self.rules["tag_catalog"]["category_tags"].values() for tag in group]
        tags += [tag for group in self.rules["tag_catalog"]["common_tags"].values() for tag in group]
        seen_tags = [tag for tag in tags if re.search(rf"#\s*{re.escape(tag)}(?=\s|$)", body)]
        self.viewed.append({"content_id": content_id, "category": category, "tags": seen_tags, "source": source})
        self.log("행사 상세 조회", "성공", f"콘텐츠 {content_id}", content_id=content_id, category=category, tags=seen_tags, source=source)

    async def _recommendation(self, page, link):
        if urlparse(page.url).path != "/recommendations":
            await link.first.click()
            await page.wait_for_url("**/recommendations")
        links = page.locator('main a[href*="/contents/"]')
        await links.first.wait_for(state="visible")
        ids = await links.evaluate_all("els => [...new Set(els.map(e => e.getAttribute('href')))]")
        self.log("추천 목록 조회", "성공", f"{len(ids)}개 콘텐츠", content_links=ids)
        await self._open_content(page, "취향 기반 추천")

    async def _purchase(self, page, button, content_id):
        self.purchase_attempts.add(content_id)
        await button.first.click()
        dialog = page.get_by_role("dialog", name="결제 확인", exact=True)
        await dialog.wait_for(state="visible")
        if "실제 금액이 청구되지 않는 체험용 결제" not in await dialog.inner_text():
            await dialog.get_by_role("button", name="취소", exact=True).click()
            self.log("콘텐츠 결제", "건너뜀", "사이트의 체험용 결제 안내를 확인할 수 없음", content_id=content_id)
            return
        await dialog.get_by_role("button", name="결제하기", exact=True).click()
        await dialog.wait_for(state="hidden")
        await page.wait_for_url("**/mypage/payments")
        self.purchased.add(content_id)
        self.log("콘텐츠 결제", "성공", "체험용 결제 완료", content_id=content_id)

    async def _review(self, page, review_box, content_id):
        self.review_attempts.add(content_id)
        rating = self.rng.choice([3, 4, 5])
        await page.get_by_role("radio", name=f"{rating}점", exact=True).check()
        tags = ", ".join(self.profile["tags"][:2])
        text = f"[시뮬레이션 리뷰] {tags} 취향으로 콘텐츠 소개와 정보를 살펴봤습니다."
        await review_box.fill(text)
        await page.get_by_role("button", name="리뷰 저장", exact=True).click()
        await page.get_by_text("리뷰를 저장했어요.", exact=True).wait_for(state="visible")
        self.reviewed.add(content_id)
        self.log("리뷰 작성", "성공", f"{rating}점 리뷰 저장", content_id=content_id)

    async def _run_browser(self):
        RUNS.mkdir(exist_ok=True)
        reason = "정상 종료"
        headless = os.getenv("ODDINARY_HEADLESS", "").lower() in {"1", "true", "yes"} or (sys.platform.startswith("linux") and not os.getenv("DISPLAY"))
        headless = self.rules["session"].get("headless", headless)
        async with async_playwright() as p:
            launch_options = {"headless": headless}
            chrome_executable = Path("C:/Program Files/Google/Chrome/Application/chrome.exe")
            if not self.rules["session"].get("chromium_only") and chrome_executable.is_file():
                launch_options["executable_path"] = str(chrome_executable)
            browser = await p.chromium.launch(**launch_options)
            context = await browser.new_context(locale="ko-KR")
            page = await context.new_page()
            page.set_default_timeout(7000)
            page.on("requestfailed", lambda request: self.log(
                "네트워크 요청", "실패", f"{request.method} {urlparse(request.url).path}: {request.failure}"
            ))
            page.on("request", lambda request: self.log(
                "네트워크 요청", "시작", f"{request.method} {urlparse(request.url).path}"
            ) if request.method in {"POST", "PUT", "PATCH"} else None)
            page.on("response", lambda response: self.log(
                "네트워크 응답", "완료", f"{response.status} {response.request.method} {urlparse(response.url).path}"
            ) if response.request.method in {"POST", "PUT", "PATCH"} else None)
            page.on("response", lambda response: self.log(
                "네트워크 응답", "실패", f"{response.status} {urlparse(response.url).path}"
            ) if response.status >= 400 else None)
            try:
                await page.goto(self.rules["site_url"], wait_until="domcontentloaded", timeout=30000)
                await page.locator("body").wait_for(state="visible", timeout=10000)
                self.log("메인 페이지 방문", "성공", await page.title())
                await self.dismiss_first_visit(page)
                if not await self.authenticate(page):
                    reason = "회원가입 또는 로그인 실패"
                    raise RuntimeError(reason)
                end_at = asyncio.get_running_loop().time() + self.rules["session"]["max_minutes"] * 60
                action_probs = self.probabilities["action_probabilities"]
                categories = self.rules["cultural_categories"]
                for _ in range(self.rules["session"]["max_actions"]):
                    if asyncio.get_running_loop().time() >= end_at:
                        reason = "세션 시간 제한"
                        break
                    candidates = []
                    weights = []
                    explore_link = page.get_by_role("link", name=re.compile("문화 탐색|오늘의 문화 발견|전체 보기"))
                    if await visible(explore_link):
                        candidates.append("explore"); weights.append(action_probs.get("content_view", .2))
                    search_open = page.get_by_role("button", name="문화 콘텐츠 검색", exact=True)
                    search_box = page.get_by_role("textbox", name=re.compile("검색어|문화 콘텐츠 검색"))
                    if await visible(search_open) or await visible(search_box):
                        candidates.append("search"); weights.append(action_probs.get("search", .2))
                    content_links = page.locator('a[href*="/contents/"]')
                    if await content_links.count():
                        candidates.append("detail"); weights.append(action_probs.get("content_view", .2))
                    recommendation = page.get_by_role("link", name=re.compile("취향 추천|나를 위한 추천|추천 더 보기"))
                    if await visible(recommendation):
                        candidates.append("recommendation"); weights.append(action_probs.get("recommendation_click", 0))
                    favorite = page.get_by_role("button", name=re.compile("찜하기$"))
                    unfavorite = page.get_by_role("button", name=re.compile("찜 취소$"))
                    if await visible(favorite) and (page.url, "add") not in self.favorite_changes:
                        candidates.append("favorite"); weights.append(action_probs.get("favorite_add", .1))
                    if await visible(unfavorite) and (page.url, "remove") not in self.favorite_changes:
                        candidates.append("unfavorite"); weights.append(action_probs.get("favorite_remove", 0))
                    match = re.search(r"/contents/(\d+)$", urlparse(page.url).path)
                    content_id = match.group(1) if match else None
                    purchase = page.get_by_role("button", name="결제하기", exact=True)
                    review_box = page.get_by_role("textbox", name="감상 리뷰", exact=True)
                    if content_id and content_id not in self.purchase_attempts and await visible(purchase):
                        candidates.append("purchase"); weights.append(action_probs.get("purchase_simulation", 0))
                    if content_id and content_id not in self.review_attempts and await visible(review_box):
                        candidates.append("review"); weights.append(action_probs.get("review_write", 0))
                    if not candidates:
                        self.log("다음 행동", "건너뜀", "현재 화면에 실행 가능한 요소가 없음")
                        break
                    if not any(weight > 0 for weight in weights):
                        self.log("다음 행동", "건너뜀", "현재 화면의 행동 확률이 모두 0")
                        break
                    action = self.rng.choices(candidates, weights=weights, k=1)[0]
                    try:
                        delay = self.rules["session"]["wait_seconds"]
                        await page.wait_for_timeout(int(self.timing_rng.uniform(*delay) * 1000))
                        if action == "explore":
                            if urlparse(page.url).path != "/explore":
                                await explore_link.first.click()
                            self.log("문화 탐색 이동", "성공", page.url)
                            # Pick a category using all six probabilities, including discovery interests.
                            cat = self.rng.choices(categories, weights=[self.probabilities["category_probabilities"][c] for c in categories], k=1)[0]
                            category_button = page.get_by_role("button", name=cat, exact=True)
                            if await visible(category_button):
                                await category_button.click()
                                await page.wait_for_timeout(250)
                                self.log("카테고리 이동", "성공", cat, category=cat)
                            else:
                                self.log("카테고리 이동", "건너뜀", f"현재 화면에 {cat} 버튼 없음", category=cat)
                        elif action == "search":
                            if not await visible(search_box) and await visible(search_open):
                                await search_open.click()
                            search_box = page.get_by_role("textbox", name=re.compile("검색어|문화 콘텐츠 검색"))
                            if not await visible(search_box):
                                self.log("행사 검색", "건너뜀", "검색 입력란이 열리지 않음")
                            else:
                                chosen_tag = self.rng.choice(self.profile["tags"])
                                query_list = self.rules.get("search_queries_by_tag", {}).get(chosen_tag, [chosen_tag])
                                query = self.rng.choice(query_list)
                                await search_box.first.fill(query)
                                submit = page.get_by_role("button", name="검색", exact=True)
                                if await visible(submit):
                                    await submit.first.click(timeout=3000)
                                else:
                                    await search_box.first.press("Enter")
                                await page.wait_for_timeout(800)
                                self.log("행사 검색", "성공", query)
                        elif action == "detail":
                            await self._open_content(page)
                        elif action == "recommendation":
                            await self._recommendation(page, recommendation)
                        elif action == "purchase":
                            await self._purchase(page, purchase, content_id)
                        elif action == "review":
                            await self._review(page, review_box, content_id)
                        elif action in {"favorite", "unfavorite"}:
                            button = (favorite if action == "favorite" else unfavorite).first
                            label = (await button.inner_text()).strip()
                            await button.click()
                            await page.wait_for_timeout(500)
                            login_prompt = await page.get_by_role("button", name=re.compile("로그인 후")).count()
                            if login_prompt:
                                self.log("행사 찜", "건너뜀", "찜 기능에 로그인이 필요함")
                            else:
                                self.favorite_changes.add((page.url, "add" if action == "favorite" else "remove"))
                                self.log("행사 찜", "성공", f"찜 상태 조작: {label}")
                    except Exception as exc:
                        self.log(action, "실패", str(exc)[:400])
                else:
                    reason = "최대 행동 수 도달"
            except Exception as exc:
                if reason == "정상 종료":
                    reason = "페이지 로딩 또는 실행 실패"
                self.log("페이지 실행", "실패", str(exc)[:500])
            finally:
                try:
                    await context.close()
                finally:
                    await browser.close()
        return reason

    async def run(self):
        RUNS.mkdir(exist_ok=True)
        started = now()
        reason = "실행 중단"
        duration = self.rules["session"].get("duration_seconds", self.rules["session"]["max_minutes"] * 60)
        try:
            # 인증과 탐색, 동작 중 대기도 포함하는 세션 전체 제한입니다.
            reason = await asyncio.wait_for(self._run_browser(), timeout=duration)
        except asyncio.TimeoutError:
            reason = "세션 시간 제한"
            self.log("세션 종료", "성공", f"활동 시간 {duration:.1f}초 도달")
        except Exception as exc:
            reason = "브라우저 실행 실패"
            self.log("페이지 실행", "실패", str(exc)[:500])
        finally:
            result = self._save_result(started, reason)
        return result

    def _save_result(self, started, reason):
        summary = {
            "content_count_by_category": dict(Counter(x["category"] for x in self.viewed if x["category"])),
            "content_count_by_tag": dict(Counter(tag for x in self.viewed for tag in x["tags"])),
            "viewed_content_ids": [x["content_id"] for x in self.viewed],
        }
        result = {"persona_id": self.persona["persona_id"], "started_at": started, "ended_at": now(), "end_reason": reason,
                  "interests": {"categories": self.profile["cultural_categories"], "tags": self.profile["tags"]},
                  "probabilities": self.probabilities, "actions": self.events, "viewed_contents": self.viewed, "summary": summary}
        output = RUNS / f"{self.persona['persona_id']}_simulation.json"
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"실행 결과 저장: {output.relative_to(ROOT)}")
        return result


async def run_simulation(persona, rules, probabilities):
    return await Simulator(persona, rules, probabilities).run()
