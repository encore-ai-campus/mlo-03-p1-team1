from datetime import date, datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, field_serializer
from app.schemas.profile import Gender, ProfileInput, Residence

CATEGORIES = ('전시', '뮤지컬', '연극', '음악', '무용', '축제')
Category = Literal['전시', '뮤지컬', '연극', '음악', '무용', '축제']


class LoginInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class SurveyInput(BaseModel):
    categories: list[Category] = Field(min_length=1, max_length=6)
    tags: list[str] = Field(default_factory=list, max_length=10)

    @field_validator('tags')
    @classmethod
    def clean_tags(cls, values: list[str]) -> list[str]:
        if any(not v.strip() or len(v) > 30 for v in values):
            raise ValueError('태그는 1–30자입니다.')
        return list(dict.fromkeys(v.strip() for v in values))


class RegisterInput(ProfileInput):
    """Create an account with optional profile fields and an initial taste survey."""

    email: EmailStr
    name: str = Field(min_length=2, max_length=40)
    password: str = Field(min_length=10, max_length=128)
    # Older callers can still register with only account credentials.
    survey: SurveyInput | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    name: str
    gender: Gender | None
    age: int | None
    age_recorded_at: datetime | None
    residence: Residence | None
    occupation: str | None
    mbti: str | None
    categories: list[str]
    tags: list[str]
    survey_completed: bool

    @field_serializer('age_recorded_at')
    def serialize_age_time(self, value):
        return value.replace(tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z') if value else None


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


class EventInput(BaseModel):
    event_id: UUID
    event_type: Literal['content_view', 'search', 'filter_use', 'recommendation_click', 'recommendation_impression']
    content_id: int | None = Field(default=None, gt=0)
    category: Category | None = None


class OrderInput(BaseModel):
    content_id: int = Field(gt=0)
    quantity: int = Field(default=1, ge=1, le=4)


class SimulatedPaymentInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    content_id: int = Field(gt=0, strict=True)
    quantity: int = Field(default=1, ge=1, le=4, strict=True)


class PaymentConfigOut(BaseModel):
    enabled: bool
    mode: Literal['simulation']
    refunds_enabled: bool
    store_id: str = ''
    channel_key: str = ''


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
    is_simulated: bool
    created_at: datetime

    @field_serializer('created_at')
    def serialize_time(self, value):
        return value.replace(tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z')


class CancelInput(BaseModel):
    reason: str = Field(min_length=2, max_length=200)
