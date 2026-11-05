from datetime import date, datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, field_serializer

CATEGORIES = ('전시', '뮤지컬', '연극', '음악', '무용', '축제')
Category = Literal['전시', '뮤지컬', '연극', '음악', '무용', '축제']


class RegisterInput(BaseModel):
    email: EmailStr
    name: str = Field(min_length=2, max_length=40)
    password: str = Field(min_length=10, max_length=128)

    @field_validator('name')
    @classmethod
    def clean_name(cls, value: str) -> str:
        if len(value.strip()) < 2:
            raise ValueError('이름은 공백 제외 두 글자 이상 입력해 주세요.')
        return value.strip()


class LoginInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class ProfileInput(BaseModel):
    name: str = Field(min_length=2, max_length=40)
    _clean = field_validator('name')(RegisterInput.clean_name.__func__)


class PreferencesInput(BaseModel):
    regions: list[Literal['서울', '경기', '인천', '부산', '대구', '광주', '대전', '울산', '세종', '강원', '충북', '충남', '전북', '전남', '경북', '경남', '제주']] = Field(default_factory=list, max_length=17)
    max_price: int | None = Field(default=None, ge=0, le=10000000)
    companions: list[Literal['혼자', '친구', '연인', '가족']] = Field(default_factory=list, max_length=4)


class SurveyInput(BaseModel):
    categories: list[Category] = Field(min_length=1, max_length=6)
    tags: list[str] = Field(default_factory=list, max_length=10)
    preferences: PreferencesInput = Field(default_factory=PreferencesInput)

    @field_validator('tags')
    @classmethod
    def clean_tags(cls, values: list[str]) -> list[str]:
        if any(not v.strip() or len(v) > 30 for v in values):
            raise ValueError('태그는 1–30자입니다.')
        return list(dict.fromkeys(v.strip() for v in values))


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    name: str
    categories: list[str]
    tags: list[str]
    survey_completed: bool
    preferences: PreferencesInput = Field(default_factory=PreferencesInput)
    is_admin: bool = False


class AuthOut(BaseModel):
    access_token: str
    token_type: str = 'bearer'
    user: UserOut


class ContentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    subtitle: str
    category: str
    region: str
    venue: str
    address: str
    latitude: float | None = None
    longitude: float | None = None
    start_date: date
    end_date: date
    price: int
    price_text: str
    description: str
    image_url: str
    source_url: str
    source: str
    tags: list[str]
    is_sample: bool
    bookable: bool
    collected_at: datetime
    bookmarked: bool = False
    rating: float | None = None
    review_count: int = 0
    recommendation_reason: str | None = None

    @field_serializer('collected_at')
    def serialize_time(self, value):
        return value.replace(tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z')


class ContentPage(BaseModel):
    items: list[ContentOut]
    total: int
    page: int = 1
    size: int = 24


class ReviewInput(BaseModel):
    rating: int = Field(ge=1, le=5)
    body: str = Field(min_length=5, max_length=2000)

    @field_validator('body')
    @classmethod
    def clean_body(cls, value: str) -> str:
        if len(value.strip()) < 5:
            raise ValueError('리뷰는 공백 제외 다섯 글자 이상 입력해 주세요.')
        return value.strip()


class ReviewOut(BaseModel):
    id: int
    user_id: int
    name: str
    rating: int
    body: str
    updated_at: datetime

    @field_serializer('updated_at')
    def serialize_time(self, value):
        return value.replace(tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z')


class UserReviewOut(ReviewOut):
    content_id: int
    content_title: str


class EventInput(BaseModel):
    event_id: UUID
    event_type: Literal['content_view', 'search', 'filter_use', 'recommendation_click', 'recommendation_impression']
    content_id: int | None = Field(default=None, gt=0)
    category: Category | None = None


class OrderInput(BaseModel):
    content_id: int = Field(gt=0)
    quantity: int = Field(default=1, ge=1, le=4)


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    payment_id: str
    content_id: int
    order_name: str
    quantity: int
    amount: int
    cancelled_amount: int
    currency: str
    status: str
    created_at: datetime

    @field_serializer('created_at')
    def serialize_time(self, value):
        return value.replace(tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z')


class CancelInput(BaseModel):
    reason: str = Field(min_length=2, max_length=200)
