from datetime import datetime

from pydantic import BaseModel, field_validator


class EventCreate(BaseModel):
    title: str
    description: str = ""
    event_type: str
    scheduled_date: datetime

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        if v not in ("speed_talk", "long_speech", "debate"):
            raise ValueError("Invalid event type")
        return v


class SpeedTalkRating(BaseModel):
    star_rating: int

    @field_validator("star_rating")
    @classmethod
    def validate_stars(cls, v: int) -> int:
        if not 1 <= v <= 5:
            raise ValueError("Rating must be between 1 and 5")
        return v


class DetailedRating(BaseModel):
    clarity: int
    confidence: int
    body_language: int
    presentation_skills: int
    content: int

    @field_validator("clarity", "confidence", "body_language", "presentation_skills", "content")
    @classmethod
    def validate_score(cls, v: int) -> int:
        if not 1 <= v <= 5:
            raise ValueError("Score must be between 1 and 5")
        return v
