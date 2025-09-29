from typing import List

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from database.database import async_session_maker
from database.models import User, Record

import datetime

# add new user to database
async def create_user(
    telegram_id: int,
    first_name: str,
    username: str | None = None,
    last_name: str | None = None,
    middle_name: str | None = None,
    phone: str | None = None,
    user_type: str | None = None
) -> User:
    async with async_session_maker() as session:
        try:
            new_user = User(
                telegram_id=telegram_id,
                first_name=first_name,
                username=username,
                last_name=last_name,
                middle_name=middle_name,
                phone=phone,
                user_type=user_type
            )

            session.add(new_user)
            await session.commit()

        except SQLAlchemyError as e:
            print(e)
            await session.rollback()

    return new_user


# check if user is in database
async def user_exist(telegram_id: int) -> bool:
    async with async_session_maker() as session:
        query = select(User).where(User.telegram_id == telegram_id)
        user_data = await session.execute(query)
        user = user_data.scalar_one_or_none()

    return user is not None


# update user data
async def update_user(
        telegram_id: int,
        first_name: str,
        username: str | None = None,
        last_name: str | None = None,
        middle_name: str | None = None,
        phone: str | None = None,
        user_type: str | None = None
) -> User:
    pass
    async with async_session_maker() as session:
        try:
            query = select(User).where(User.telegram_id == telegram_id)
            user_data = await session.execute(query)
            user = user_data.scalar_one_or_none()

            user.telegram_id = telegram_id
            user.first_name = first_name
            user.username = username
            user.last_name = last_name
            user.middle_name = middle_name
            user.phone = phone
            user.user_type = user_type

            await session.commit()
        except SQLAlchemyError as e:
            print(e)
            await session.rollback()

    return user


# create new record of booking a room
async def create_record(
    telegram_id: int,
    building: str,
    room: str,
    date: datetime.date,
    time_slot: str
):
    async with async_session_maker() as session:
        try:
            record = Record(
                user_id=telegram_id,
                building=building,
                room=room,
                date=date,
                time_slot=time_slot
            )

            session.add(record)
            await session.commit()

        except SQLAlchemyError as e:
            print(e)
            await session.rollback()


# get list of all records for a specific user
async def get_user_records(telegram_id: int) -> List[Record]:
    async with async_session_maker() as session:
        try:
            query = select(Record).where(Record.user_id == telegram_id)
            users_data = await session.execute(query)
            users = users_data.scalars().all()

        except SQLAlchemyError as e:
            print(e)

    return users

# get records by date and room number
async def get_records_by_date_room(date: datetime.date, room: str) -> List[Record]:
    async with async_session_maker() as session:
        try:
            query = select(Record).where(Record.date == date).where(Record.room == room)
            records_data = await session.execute(query)
            records = records_data.scalars().all()
        except SQLAlchemyError as e:
            print(e)

    return records


# get records by building
async def get_records_by_building(building: str) -> List[Record]:
    async with async_session_maker() as session:
        try:
            current_date = datetime.datetime.now(datetime.UTC).date()
            query = select(Record).where(Record.date >= current_date).where(Record.building == building)
            records_data = await session.execute(query)
            records = records_data.scalars().all()
        except SQLAlchemyError as e:
            print(e)

    return records