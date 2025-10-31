from typing import List

from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.exc import SQLAlchemyError

from config import config
from database.database import async_session_maker
from database.models import User, Record

from datetime import datetime, UTC, timedelta

async def create_user(
    telegram_id: int,
    full_name: str,
    username: str | None = None,
    email: str | None = None,
    user_type: str | None = None
) -> User:
    async with async_session_maker() as session:
        try:
            new_user = User(
                telegram_id=telegram_id,
                full_name=full_name,
                username=username,
                email=email,
                user_type=user_type,
                email_verified=True  # Set to True since we verified it
            )

            session.add(new_user)
            await session.commit()

        except SQLAlchemyError as e:
            print(e)
            await session.rollback()
    return new_user


# get user by telegram id
async def get_user(telegram_id: int) -> User | None:
    async with async_session_maker() as session:
        try:
            query = select(User).where(User.telegram_id == telegram_id)
            user = await session.execute(query)
            user = user.scalar_one_or_none()
            return user
        except SQLAlchemyError as e:
            print(e)



# check if user is in database
async def user_exist(telegram_id: int) -> bool:
    async with async_session_maker() as session:
        query = select(User).where(User.telegram_id == telegram_id)
        user_data = await session.execute(query)
        user = user_data.scalar_one_or_none()

    return user is not None


# update user data
async def update_user(telegram_id:int, **kwargs) -> User:
    async with async_session_maker() as session:
        try:
            statement = update(User).where(User.telegram_id == telegram_id).values(**kwargs)
            await session.execute(statement)

            await session.commit()
        except SQLAlchemyError as e:
            print(e)
            await session.rollback()

    return await get_user(telegram_id)


# delete user
async def delete_user(telegram_id: int):
    async with async_session_maker() as session:
        try:
            statement = delete(User).where(User.telegram_id == telegram_id)
            await session.execute(statement)
            await session.commit()
        except SQLAlchemyError as e:
            print(e)


# create new record of booking a room
async def create_record(
    telegram_id: int,
    building: str,
    room: str,
    date: datetime.date,
    time_slot_start: datetime.time,
    time_slot_end: datetime.time
):
    async with async_session_maker() as session:
        try:
            record = Record(
                user_id=telegram_id,
                building=building,
                room=room,
                date=date,
                time_slot_start=time_slot_start,
                time_slot_end=time_slot_end
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


# get list of records for specific building, room, date
async def get_records_by_building_room_date(building: str, room:str, date:datetime.date) -> List[Record]:
    records: List[Record] = []
    async with async_session_maker() as session:
        try:
            query = select(Record).where(Record.building == building, Record.room == room, Record.date == date)
            records_data = await session.execute(query)
            records = records_data.scalars().all()
        except SQLAlchemyError as e:
            print(e)

    return records

# check database if room available at this time
async def is_room_recorded(building: str, room: str, date: datetime.date, start:datetime.time, end: datetime.time) -> bool:
    result = True
    async with async_session_maker() as session:
        try:
            query = select(Record).where(Record.building == building, Record.room == room, Record.date == date, Record.time_slot_start == start, Record.time_slot_end == end)
            records_data = await session.execute(query)
            record = records_data.scalar_one_or_none()

            result = record is not None
        except SQLAlchemyError as e:
            print(e)

    return result

# get record if room is booked, else return None
async def check_if_booked(building: str, room: str, date: datetime.date, start:datetime.time, end: datetime.time):
    async with async_session_maker() as session:
        try:
            query = select(Record).where(
                Record.building == building,
                Record.room == room,
                Record.date == date,
                Record.time_slot_start == start,
                Record.time_slot_end == end
            ).options(selectinload(Record.user))
            record_data = await session.execute(query)
            record = record_data.scalar_one_or_none()

            if record:
                user = record.user

            return record
        except SQLAlchemyError as e:
            print(e)

# # get records by date and room number
# async def get_records_by_date_room(date: datetime.date, room: str) -> List[Record]:
#     async with async_session_maker() as session:
#         try:
#             query = select(Record).where(Record.date == date).where(Record.room == room)
#             records_data = await session.execute(query)
#             records = records_data.scalars().all()
#         except SQLAlchemyError as e:
#             print(e)
#
#     return records


# get records by building
async def get_records_by_building(building: str) -> List[Record]:
    async with async_session_maker() as session:
        try:
            current_date = datetime.now(UTC).date()
            query = select(Record).where(Record.date >= current_date).where(Record.building == building)
            records_data = await session.execute(query)
            records = records_data.scalars().all()
        except SQLAlchemyError as e:
            print(e)

    return records

async def get_all_records() -> List[Record] | None:
    async with async_session_maker() as session:
        try:
            query = select(Record).options(selectinload(Record.user))
            data_records = await session.execute(query)
            records = data_records.scalars().all()

            for r in records:
                _ = r.user

            return records
        except SQLAlchemyError as e:
            print(e)



async def get_all_records_n_days() -> List[Record] | None:
    start_date = datetime.now(UTC) + timedelta(hours=config.TIMEZONE, days=-1 * config.DAYS_TO_LOAD_FROM_DB)

    async with async_session_maker() as session:
        try:
            query = select(Record).where(Record.date >= start_date.date()).order_by(Record.date, Record.time_slot_start).options(selectinload(Record.user))
            data_records = await session.execute(query)
            records = data_records.scalars().all()

            for r in records:
                _ = r.user

            return records
        except SQLAlchemyError as e:
            print(e)


# Deleting records that are config.DAYS_TO_LOAD_FROM_DB days old
async def delete_old_records() -> bool:
    end_date = datetime.now(UTC) + timedelta(hours=config.TIMEZONE, days=-1 * config.DAYS_TO_LOAD_FROM_DB)

    async with async_session_maker() as session:
        try:
            statement = delete(Record).where(Record.date < end_date.date())
            await session.execute(statement)

            session.commit()
            return True
        except SQLAlchemyError as e:
            print(e)
            return False