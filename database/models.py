from database.database import Base
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy import BigInteger, ForeignKey, Integer, String, Date
from datetime import date

class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(String, nullable=True)
    first_name: Mapped[str] = mapped_column(String, nullable=True)
    last_name: Mapped[str] = mapped_column(String, nullable=True)
    middle_name: Mapped[str] = mapped_column(String, nullable=True)
    phone: Mapped[str] = mapped_column(String, nullable=True)
    email: Mapped[str] = mapped_column(String, nullable=True)
    user_type: Mapped[str] = mapped_column(String, nullable=True) # student | teacher | employee

    # relationships
    records = relationship("Record", back_populates="user")

    def to_dict(self):
        return {
            "telegram_id": self.telegram_id,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "middle_name": self.middle_name,
            "phone": self.phone,
            "email": self.email,
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
    time_slot: Mapped[str] = mapped_column(String, default=None)

    # relationships
    user = relationship("User", back_populates="records")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "building": self.building,
            "room": self.room,
            "date": self.date,
            "time_slot": self.time_slot,
            "created_at": self.created_at
        }
