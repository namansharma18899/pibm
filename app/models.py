from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    picture_url: Mapped[str | None] = mapped_column(String, nullable=True)
    google_sub: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False, default="student")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    participations: Mapped[list["Participation"]] = relationship(back_populates="student")
    ratings_given: Mapped[list["Rating"]] = relationship(back_populates="rater")
    events_created: Mapped[list["Event"]] = relationship(back_populates="created_by")


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    scheduled_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="upcoming")
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    created_by: Mapped["User"] = relationship(back_populates="events_created")
    participations: Mapped[list["Participation"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )

    @property
    def event_type_display(self) -> str:
        return {"speed_talk": "Speed Talk", "long_speech": "Long Speech", "debate": "Debate"}.get(
            self.event_type, self.event_type
        )

    @property
    def status_display(self) -> str:
        return {
            "upcoming": "Upcoming",
            "in_progress": "In Progress",
            "completed": "Completed",
        }.get(self.status, self.status)


class Participation(Base):
    __tablename__ = "participations"
    __table_args__ = (UniqueConstraint("event_id", "student_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(Integer, ForeignKey("events.id"), nullable=False)
    student_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    attended: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    event: Mapped["Event"] = relationship(back_populates="participations")
    student: Mapped["User"] = relationship(back_populates="participations")
    ratings: Mapped[list["Rating"]] = relationship(
        back_populates="participation", cascade="all, delete-orphan"
    )

    @property
    def average_score(self) -> float | None:
        if not self.ratings:
            return None
        if self.event.event_type == "speed_talk":
            scores = [r.star_rating for r in self.ratings if r.star_rating is not None]
            return sum(scores) / len(scores) if scores else None
        else:
            avgs = []
            for r in self.ratings:
                vals = [
                    v
                    for v in [
                        r.clarity,
                        r.confidence,
                        r.body_language,
                        r.presentation_skills,
                        r.content,
                    ]
                    if v is not None
                ]
                if vals:
                    avgs.append(sum(vals) / len(vals))
            return sum(avgs) / len(avgs) if avgs else None


class Rating(Base):
    __tablename__ = "ratings"
    __table_args__ = (UniqueConstraint("participation_id", "rater_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    participation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("participations.id"), nullable=False
    )
    rater_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    star_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    clarity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    body_language: Mapped[int | None] = mapped_column(Integer, nullable=True)
    presentation_skills: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    participation: Mapped["Participation"] = relationship(back_populates="ratings")
    rater: Mapped["User"] = relationship(back_populates="ratings_given")

    @property
    def category_average(self) -> float | None:
        vals = [
            v
            for v in [
                self.clarity,
                self.confidence,
                self.body_language,
                self.presentation_skills,
                self.content,
            ]
            if v is not None
        ]
        return sum(vals) / len(vals) if vals else None
