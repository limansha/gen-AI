from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import String, DateTime, Index, Integer, Boolean, ForeignKey, Text
from sqlalchemy.types import UUID as SQLAlchemyUUID, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        SQLAlchemyUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    google_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        Index("idx_google_id", "google_id"),
        Index("idx_email", "email"),
    )


class JourneyModel(Base):
    __tablename__ = "journeys"

    id: Mapped[UUID] = mapped_column(
        SQLAlchemyUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    
    journey_summary: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    
    journey_traits: Mapped[list[dict]] = mapped_column(
        JSON,
        nullable=False,
    )
    
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    actions: Mapped[list["JourneyActionModel"]] = relationship(
        "JourneyActionModel",
        back_populates="journey",
        cascade="all, delete-orphan",
        order_by="JourneyActionModel.action_order",
    )

    __table_args__ = (
        Index("idx_journey_summary", "journey_summary"),
    )


class JourneyActionModel(Base):
    __tablename__ = "journey_actions"

    id: Mapped[UUID] = mapped_column(
        SQLAlchemyUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    
    journey_id: Mapped[UUID] = mapped_column(
        SQLAlchemyUUID(as_uuid=True),
        ForeignKey("journeys.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    action_title: Mapped[str] = mapped_column(String(255), nullable=False)
    action_duration: Mapped[str] = mapped_column(String(50), nullable=False)
    action_steps: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    action_order: Mapped[int] = mapped_column(Integer, nullable=False)
    
    is_completed: Mapped[bool] = mapped_column(
        Boolean, 
        default=False, 
        nullable=False, 
        index=True
    )

    journey: Mapped["JourneyModel"] = relationship(
        "JourneyModel",
        back_populates="actions",
    )

    __table_args__ = (
        Index("idx_journey_id_order", "journey_id", "action_order"),
        Index("idx_journey_completed", "journey_id", "is_completed"),
    )

