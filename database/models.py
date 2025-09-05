from database.database import Base
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy import BigInteger, ForeignKey, Integer, String, Date

class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[Integer] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[String] = mapped_column(String, nullable=True)
    first_name: Mapped[String] = mapped_column(String, nullable=False)
    last_name: Mapped[String] = mapped_column(String, nullable=False)
    middle_name: Mapped[String] = mapped_column(String, nullable=True)
    phone: Mapped[String] = mapped_column(String, nullable=True)
    type: Mapped[String] = mapped_column(String, nullable=True) # student | teacher | employee

    # relationships
    records = relationship("Record", back_populates="user")

class Record(Base):
    __tablename__ = "records"

    id: Mapped[Integer] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[Integer] = mapped_column(ForeignKey("users.telegram_id"))
    building: Mapped[String] = mapped_column(String, default=False)
    room: Mapped[String] = mapped_column(String, default=False)
    date: Mapped[Date] = mapped_column(Date, default=None)
    time_slot: Mapped[String] = mapped_column(String, default=None)

    # relationships
    user = relationship("User", back_populates="records")
