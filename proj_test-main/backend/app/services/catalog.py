from collections import defaultdict
import math

from fastapi import HTTPException

from app.core.security import utcnow
from app.models import Review
from app.repositories.store import Store
from app.schemas import ContentOut, ReviewOut


class CatalogService:
    def __init__(self, store: Store):
        self.store = store

    def require(self, content_id):
        content = self.store.content(content_id)
        if not content:
            raise HTTPException(404, '콘텐츠를 찾을 수 없습니다.')
        return content

    def serialize(self, contents, user=None):
        ratings, marked = self.store.enrich(contents, user.id if user else None)
        result = []
        for content in contents:
            obj = ContentOut.model_validate(content)
            obj.bookmarked = content.id in marked
            obj.rating, obj.review_count = ratings.get(content.id, (None, 0))
            result.append(obj)
        return result

    def recommendations(self, user, size):
        candidates, _ = self.store.contents(sort='popular', size=500)
        categories = defaultdict(float)
        tags = defaultdict(float)
        if user:
            for cat in user.categories:
                categories[cat] += 5
            for tag in user.tags:
                tags[tag] += 3
            # Deduplicate repeated views per content/day so refreshes cannot dominate.
            seen = set()
            events = self.store.events(user.id)
            content_ids = {e.content_id for e in events if e.content_id}
            viewed = {c.id: c for c in self.store.contents_by_ids(content_ids)}
            for event in events:
                key = (event.content_id, event.event_type, event.occurred_at.date())
                if key in seen:
                    continue
                seen.add(key)
                content = viewed.get(event.content_id)
                weight = {'content_view': 1, 'recommendation_click': 2}.get(event.event_type, 0)
                decay = math.exp(-max(0, (utcnow() - event.occurred_at).days) / 30)
                if content:
                    categories[content.category] += weight * decay
                    for tag in content.tags:
                        tags[tag] += weight * decay * .5
            for content in self.store.bookmarks(user.id):
                categories[content.category] += 3
                for tag in content.tags:
                    tags[tag] += 1.5
        preferences = user.preferences if user else {}
        def score(content):
            value = categories[content.category] + sum(tags[t] for t in content.tags)
            if content.region in preferences.get('regions', []):
                value += 3
            budget = preferences.get('max_price')
            if budget is not None and (content.price > 0 or content.price_text == '무료'):
                value += 2 if content.price <= budget else -3
            if '가족' in preferences.get('companions', []) and '가족' in content.tags:
                value += 2
            return value
        ranked = sorted(enumerate(candidates), key=lambda pair: (score(pair[1]), -pair[0]), reverse=True)
        items = self.serialize([c for _, c in ranked[:size]], user)
        for item in items:
            matching = next((t for t in item.tags if tags[t] > 0), None)
            item.recommendation_reason = f'관심 태그 #{matching}와 어울려요' if matching else (
                f'{item.category} 취향과 활동을 바탕으로 골랐어요' if categories[item.category] > 0 else '새로운 취향을 발견해 보세요')
        return items

    def save_review(self, user, content_id, data):
        self.require(content_id)
        # User lock serializes two concurrent first-review requests.
        self.store.lock_user(user.id)
        review = self.store.review(user.id, content_id)
        if review is None:
            review = self.store.add(Review(user_id=user.id, content_id=content_id, **data.model_dump()))
        else:
            review.rating, review.body = data.rating, data.body
            review.updated_at = utcnow()
        return ReviewOut(id=review.id, user_id=user.id, name=user.name, rating=review.rating, body=review.body, updated_at=review.updated_at)

    def delete_review(self, user, content_id):
        review = self.store.review(user.id, content_id)
        if review:
            self.store.delete(review)
        return {'ok': True}
