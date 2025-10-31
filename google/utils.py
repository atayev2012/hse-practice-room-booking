from datetime import datetime, timedelta, time, UTC, date
import asyncio
from typing import List

from config import config
from google.connection import conn
import copy

# GLOBAL VARIABLES
WEEKDAYS_NAMES = {
    0: "Понедельник",
    1: "Вторник",
    2: "Среда",
    3: "Четверг",
    4: "Пятница",
    5: "Суббота",
    6: "Воскресенье",
}

WEEKDAYS_NUMBERS = {
    "Понедельник": 0,
    "Вторник": 1,
    "Среда": 2,
    "Четверг": 3,
    "Пятница": 4,
    "Суббота": 5,
    "Воскресенье": 6,
}

TIME_SLOTS = [
    {"start": time(hour=8, minute=0), "end": time(hour=9, minute=20)},
    {"start": time(hour=9, minute=30), "end": time(hour=10, minute=50)},
    {"start": time(hour=11, minute=10), "end": time(hour=12, minute=30)},
    {"start": time(hour=13, minute=0), "end": time(hour=14, minute=20)},
    {"start": time(hour=14, minute=40), "end": time(hour=16, minute=0)},
    {"start": time(hour=16, minute=20), "end": time(hour=17, minute=40)},
    {"start": time(hour=18, minute=10), "end": time(hour=19, minute=30)},
    {"start": time(hour=19, minute=40), "end": time(hour=21, minute=0)}
]

BUILDINGS = {
        "сормово": "Сормовское ш., 30",
        "родионова": "ул. Родионова, 136",
        "львовская": "ул. Львовская, 1в",
        "б.печерская": "ул. Большая Печерская, 25/12",
        "костина": "ул. Костина, 2",
    }


class TimeSlot:
    def __init__(self, start: time, end: time):
        self.start = start
        self.end = end

    def export_for_keyboard(self):
        class_period = 1
        for i in range(len(TIME_SLOTS)):
            if self.start == TIME_SLOTS[i]["start"]:
                class_period += i
                break

        return class_period, f"{self.start.strftime('%H:%M')}-{self.end.strftime('%H:%M')}"

    def __copy__(self):
        new_item = TimeSlot(
            time(hour=self.start.hour, minute=self.start.minute),
            time(hour=self.end.hour, minute=self.end.minute)
        )
        return new_item

    def __eq__(self, other):
        return self.start == other.start and self.end == other.end

    def __repr__(self):
        return f"{self.start.strftime('%H:%M')}-{self.end.strftime('%H:%M')}"


class DateTimeSlot:
    def __init__(self, target_datetime: datetime, is_new: bool = True):
        self.date = target_datetime.date()
        self.time_slots = []
        if is_new:
            self.__set_weekday()
            self.__set_time_slots(target_datetime)

    def date_to_str(self):
        return datetime.strftime(self.date, "%d.%m.%Y")

    def __set_weekday(self):
        self.weekday = WEEKDAYS_NAMES.get(self.date.weekday())

    def __set_time_slots(self, target_datetime: datetime):
        # copy time slots
        for slot in TIME_SLOTS:
            if slot.get("start") > target_datetime.time():
                self.time_slots.append(TimeSlot(slot.get("start"), slot.get("end")))

    def __copy__(self):
        new_item = DateTimeSlot(datetime(year=self.date.year, month=self.date.month, day=self.date.day), is_new=False)
        for slot in self.time_slots:
            new_item.time_slots.append(copy.copy(slot))

        if hasattr(self, "weekday"):
            new_item.weekday = self.weekday

        return new_item

    def __repr__(self):
        return f"Date: {self.date.strftime('%d.%m.%Y')} {self.weekday} | Time Slots: {self.time_slots}"


# class to get list of latest dates required to show to user
class DatesRequired:
    def __init__(self):
        self.dates= []
        self.__set_dates()

    def __set_dates(self):
        # current time in specific time zone
        current_datetime = datetime.now(UTC) + timedelta(hours=config.TIMEZONE)

        # if time already passed 19:00, then moveto the next day
        if current_datetime.time() > time(hour=19, minute=40):
            current_datetime += timedelta(hours=24 - current_datetime.hour)


        for i in range(config.DAYS_TO_SHOW):
            target_datetime = current_datetime + timedelta(days=i)

            # if date is not today, start from time 00:00 for the next days
            if target_datetime != current_datetime:
                target_datetime -= timedelta(hours=target_datetime.hour, minutes=target_datetime.minute)

            self.dates.append(DateTimeSlot(target_datetime))

    def __repr__(self):
        return f"DatesRequired: {self.dates}"


class WeekdayTimeSlot:
    def __init__(self, weekday: int | str, need_fill_time_slots: bool = True):
        if isinstance(weekday, int):
            self.weekday_name = WEEKDAYS_NAMES.get(weekday)
        elif isinstance(weekday, str):
            self.weekday_name = weekday

        self.time_slots = []

        if need_fill_time_slots:
            self.__fill_with_time_slots()

    def __fill_with_time_slots(self):
        for slot in TIME_SLOTS:
            self.time_slots.append(TimeSlot(slot.get("start"), slot.get("end")))

    def __copy__(self):
        new_item = WeekdayTimeSlot(weekday=self.weekday_name, need_fill_time_slots=False)
        for slot in self.time_slots:
            new_item.time_slots.append(copy.copy(slot))
        return new_item

    def __repr__(self):
        return f"Weekday: {self.weekday_name} | Time Slots: {self.time_slots}\n"


class Room:
    def __init__(self, room_number: str, capacity: str, equipment: list, zoom: bool = False, need_fill_time_slot: bool = True, is_copy: bool = False):
        self.room_number = room_number
        self.capacity = capacity
        self.equipment = equipment
        self.zoom = zoom
        self.weekdays = []

        if not is_copy:
            self.__fill_weekdays(need_fill_time_slot)

    def __fill_weekdays(self, need_fill_time_slots: bool):
        for weekday in range(7):
            self.weekdays.append(
                WeekdayTimeSlot(weekday=weekday, need_fill_time_slots=need_fill_time_slots)
            )

    def __copy__(self):
        new_item = Room(
            room_number=self.room_number,
            capacity=self.capacity,
            equipment=copy.copy(self.equipment),
            need_fill_time_slot=False,
            is_copy=True
        )

        for weekday in self.weekdays:
            new_item.weekdays.append(copy.copy(weekday))

        return new_item

    def __repr__(self):
        return f"Room: #{self.room_number} | Capacity: {self.capacity} | Equipment: {self.equipment} | Zoom: {self.zoom}\n\t\tWeekdays: {self.weekdays}\n"


class Building:
    def __init__(self, building_name: str, building_address: str):
        self.building_name = building_name
        self.address = building_address
        self.rooms = []

    def add_rooms(self, rooms: list[Room]):
        self.rooms.extend(rooms)

    def __copy__(self):
        new_item = Building(self.building_name, self.address)
        for room in self.rooms:
            new_item.rooms.append(copy.copy(room))
        return new_item

    def __repr__(self):
        return f"Building: {self.building_name} | Address: {self.address}\n\tRooms: [{self.rooms}]\n"


class ScheduleParser:
    def __init__(self, is_global: bool = False):
        self.buildings = []

        if is_global:
            self.lock = asyncio.Lock()
        else:
            self.__import_schedule()

    async def get_time_slots_by_building_room_weekday(self, building_name, room_number: str, weekday: str) -> List[WeekdayTimeSlot]:
        time_slots: List[WeekdayTimeSlot] = []
        async with self.lock:
            for building in self.buildings:
                if building.building_name == building_name:
                    for room in building.rooms:
                        if room.room_number == room_number:
                            for weekday_obj in room.weekdays:
                                if weekday_obj.weekday_name == weekday:
                                    time_slots.extend(copy.copy(weekday_obj.time_slots))

        return time_slots

    async def get_buildings_dict(self) -> dict:
        buildings_dict = {}
        async with self.lock:
            for building in self.buildings:
                buildings_dict[building.building_name] = building.address

        return buildings_dict


    async def get_rooms_list_by_building_name(self, building_name: str) -> list:
        rooms = []
        async with self.lock:
            for building in self.buildings:
                if building.building_name == building_name:
                    for room in building.rooms:
                        rooms.append(room.room_number)
                    break

        return rooms


    async def get_weekdays_by_building_room(self, building_name: str, room_number: str) -> list[WeekdayTimeSlot]:
        async with self.lock:
            for building in self.buildings:
                if building.building_name == building_name:
                    for room in building.rooms:
                        if room.room_number == room_number:
                            weekdays_list = copy.copy(room.weekdays)
        return weekdays_list


    def __copy__(self):
        new_item = ScheduleParser(is_global=True)
        for building in self.buildings:
            new_item.buildings.append(copy.copy(building))
        return new_item

    async def update_schedule(self):
        schedule = ScheduleParser()
        async with self.lock:
            self.buildings.clear()
            for building in schedule.buildings:
                self.buildings.append(copy.copy(building))

    def __import_schedule(self):
        # Fetch sheet metadata
        metadata = conn.spreadsheet.fetch_sheet_metadata(params={'fields': 'sheets.merges'})

        for worksheet in conn.spreadsheet.worksheets():
            # load all values
            worksheet_data = worksheet.get_all_values()

            # Copy data to empty merged cells
            for merges in metadata["sheets"]:
                for merge in merges["merges"]:
                    if merge.get("sheetId") == worksheet.id or (merge.get("sheetId") is None and worksheet.id == 0):
                        for i in range(merge["startRowIndex"], merge["endRowIndex"]):
                            for j in range(merge["startColumnIndex"], merge["endColumnIndex"]):
                                if not (i == merge["startRowIndex"] and j == merge["startColumnIndex"]):
                                    worksheet_data[i][j] = worksheet_data[merge["startRowIndex"]][
                                        merge["startColumnIndex"]]

            # Building name from spreadsheet
            building_name = worksheet.title.lower()

            # If address is available for the building, then use address, otherwise use name as address
            if BUILDINGS.get(building_name):
                building_address = BUILDINGS.get(building_name)
            else:
                building_address = building_name

            # Create building sample
            building = Building(building_name, building_address)

            rooms = []

            # Start parsing
            for i, room_number in enumerate(worksheet_data[1][2:]):
                room_number = room_number.lower().replace("\n", " ").replace("  ", " ")
                zoom = False
                if worksheet_data[2][i + 2] != "" or worksheet_data[3][i + 2] != "":
                    # Coworking title and Room Numbers entered wrong, that is the fix
                    if room_number == "коворкинг":
                        room_number = worksheet_data[2][i + 2]
                        worksheet_data[1][i + 2] = room_number
                        worksheet_data[2][i + 2] = ""

                    if worksheet_data[0][i + 2].lower() == "zoom":
                        zoom = True

                    # Some equipment is divided by "\n" and some by "/"
                    if "/" in worksheet_data[2][i + 2]:
                        # changing "/" to "\n"
                        worksheet_data[2][i + 2] = worksheet_data[2][i + 2].replace("/", "\n")

                    # List of equipment to specific room (* -> x for dimensions like 90*1200 -> 90x1200)
                    equipment = [k.strip().lower().replace("*", "x") for k in worksheet_data[2][i + 2].split("\n") if k.strip() != ""]

                    # Room capacity (max)
                    capacity = worksheet_data[3][i + 2].lower().replace("\n", " ").replace("  ", " ")

                    # Creating room sample
                    new_room = Room(
                        room_number=room_number,
                        capacity=capacity,
                        equipment=equipment,
                        zoom=zoom,
                        need_fill_time_slot=False
                    )

                    # Update time slots available
                    for k, weekday in enumerate(new_room.weekdays):
                        weekday_no = WEEKDAYS_NUMBERS.get(weekday.weekday_name)
                        for j in range(len(TIME_SLOTS)):
                            row = 9 * weekday_no + j + 4 # To locate exact row for each day and time slot

                            if worksheet_data[row][i + 2].strip() == "":
                                new_room.weekdays[k].time_slots.append(
                                    TimeSlot(start=TIME_SLOTS[j]["start"], end=TIME_SLOTS[j]["end"])
                                )

                    # Adding room to rooms list
                    rooms.append(new_room)

            # Add rooms to building list
            building.add_rooms(rooms)
            # Add buildings to building list
            self.buildings.append(building)

    def __repr__(self):
        return f"Buildings: {self.buildings}"

