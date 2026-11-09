from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Gender = Literal['female', 'male', 'other', 'prefer_not_to_say']
Residence = Literal['서울', '부산', '대구', '인천', '광주', '대전', '울산', '세종',
                    '경기', '강원', '충북', '충남', '전북', '전남', '경북', '경남', '제주', '해외']


class ProfileInput(BaseModel):
    """Omitted fields stay unchanged; null clears an optional demographic field."""

    model_config = ConfigDict(extra='forbid')

    name: str | None = Field(default=None, min_length=2, max_length=40)
    gender: Gender | None = None
    age: int | None = Field(default=None, ge=0, le=120, strict=True)
    residence: Residence | None = None
    occupation: str | None = Field(default=None, max_length=80)
    mbti: str | None = Field(default=None, pattern=r'^[EI][NS][FT][JP]$')

    @field_validator('name')
    @classmethod
    def clean_name(cls, value: str | None) -> str:
        if value is None or len(value.strip()) < 2:
            raise ValueError('이름은 공백 제외 두 글자 이상 입력해 주세요.')
        return value.strip()

    @field_validator('occupation', 'mbti', mode='before')
    @classmethod
    def clean_optional_text(cls, value):
        if isinstance(value, str):
            return value.strip() or None
        return value

    @field_validator('mbti', mode='before')
    @classmethod
    def uppercase_mbti(cls, value):
        return value.upper() if isinstance(value, str) else value
