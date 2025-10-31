from database.database import Base
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy import BigInteger, ForeignKey, Integer, String, Date, Time, Boolean
from datetime import date, time

class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(String, nullable=True)
    full_name: Mapped[str] = mapped_column(String, nullable=True)
    phone: Mapped[str] = mapped_column(String, nullable=True)
    email: Mapped[str] = mapped_column(String, nullable=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    user_type: Mapped[str] = mapped_column(String, nullable=True) # student | teacher | employee

    # relationships
    records: Mapped[list["Record"]] = relationship("Record", back_populates="user")

    def to_dict(self):
        return {
            "telegram_id": self.telegram_id,
            "username": self.username,
            "full_name": self.full_name,
            "phone": self.phone,
            "email": self.email,
            "email_verified": self.email_verified,
            "user_type": self.user_type,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }


class Record(Base):
    __tablename__ = "records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"))
    building: Mapped[str] = mapped_column(String, default=False)
    room: Mapped[str] = mapped_column(String, default=False)
    date: Mapped[date] = mapped_column(Date, default=None)
    time_slot_start: Mapped[time] = mapped_column(Time, default=None)
    time_slot_end: Mapped[time] = mapped_column(Time, default=None)

    # relationships
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], back_populates="records")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "building": self.building,
            "room": self.room,
            "date": self.date,
            "time_slot_start": self.time_slot_start,
            "time_slot_end": self.time_slot_end,
            "user": self.user.to_dict(),
            "created_at": self.created_at
        }
