from datetime import datetime, timedelta, time, UTC, date
import asyncio
from config import config
import copy
from google.connection import conn
import re
from database.utils import check_if_booked


# GLOBAL VARIABLES
BUILDINGS = {
    "сормово": "Сормовское ш., 30",
    "родионова": "ул. Родионова, 136",
    "львовская": "ул. Львовская, 1в",
    "б.печерская": "ул. Большая Печерская, 25/12",
    "костина": "ул. Костина, 2",
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

# Status of time slot if it is free or not
class TimeSlotStatus:
    """
    Represents a time slot status.

    Attributes:
        is_free (bool): "True" if booked and "False" if not.
        name (str): person name who booked the slot.
        comment (str): reason for booking the room.
    """
    def __init__(self, is_free: bool = True, name: str = None, comment: str = None):
        self.is_free = is_free
        self.name = name
        self.comment = comment

    def __repr__(self):
        return f"(Status: free={self.is_free} who={self.name} detail={self.comment})"


# Time slot for Calendar schedule
class TimeSlot:
    """
    Represents a time slot within a day.

    Attributes:
        start (datetime.time): start time of the time slot.
        end (datetime.time): end time of the time slot.
        status (TimeSlotStatus): status of the time slot.
    """
    def __init__(self, start: time, end: time):
        self.start = start
        self.end = end
        self.status = TimeSlotStatus()


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
        """
        Returns:
             str: String representation of the time slot. Ex: "14:40-16:00"
        """
        return f"{self.start.strftime('%H:%M')}-{self.end.strftime('%H:%M')} {self.status}"


# Date item for Calendar Schedule
class DateCell:
    """
        Represents a date cell within a calendar.

        Attributes:
            time (datetime.time): time of the day when calendar date cell was created.
            date (datetime.date): date of the day when calendar date cell was created.
            weekday (str): weekday of the day when calendar date cell was created.
            time_slots (list[TimeSlot]): list of time slots within a calendar date and time.
        """
    time_slots_template = [
        TimeSlot(time(hour=8, minute=0), time(hour=9, minute=20)),
        TimeSlot(time(hour=9, minute=30), time(hour=10, minute=50)),
        TimeSlot(time(hour=11, minute=10), time(hour=12, minute=30)),
        TimeSlot(time(hour=13, minute=0), time(hour=14, minute=20)),
        TimeSlot(time(hour=14, minute=40), time(hour=16, minute=0)),
        TimeSlot(time(hour=16, minute=20), time(hour=17, minute=40)),
        TimeSlot(time(hour=18, minute=10), time(hour=19, minute=30)),
        TimeSlot(time(hour=19, minute=40), time(hour=21, minute=0))
    ]

    def __init__(self, target_datetime: datetime, is_new: bool = True):
        self.time = target_datetime.time()
        self.date = target_datetime.date()
        self.time_slots = []
        self.__set_weekday()

        if is_new:
            self.__set_time_slots()

    def date_to_str(self):
        return datetime.strftime(self.date, "%d.%m.%Y")

    def __set_time_slots(self):
        for slot in self.time_slots_template:
            if slot.end > self.time:
                self.time_slots.append(copy.copy(slot))

    def __set_weekday(self):
        weekday_names = {
            0: "Понедельник",
            1: "Вторник",
            2: "Среда",
            3: "Четверг",
            4: "Пятница",
            5: "Суббота",
            6: "Воскресенье"
        }

        self.weekday = weekday_names[self.date.weekday()]

    def get_time_slot_index(self, time_slot: TimeSlot):
        return self.time_slots.index(time_slot)

    def __copy__(self):
        new_date_cell =  DateCell(
            target_datetime=datetime.combine(self.date, self.time),
            is_new=False
        )

        for slot in self.time_slots:
            new_date_cell.time_slots.append(copy.copy(slot))

        return new_date_cell

    def __repr__(self):
        return f"Date Cell: {self.time.strftime("%H:%M:%S")} {self.date.strftime('%d.%m.%Y')} {self.weekday}\n\tTime Slots: {self.time_slots}"


class Room:
    def __init__(self, room_number: str = None, room_type: str = None, capacity: int = None, equipment: list = None, zoom: bool = False):
        self.room_number: str = room_number
        self.room_type: str = room_type
        self.capacity: int = capacity
        self.equipment: list = equipment
        self.zoom: bool = zoom
        self.dates: list = []


    def __copy__(self):
        return Room(self.room_number, self.room_type, self.capacity, self.equipment, self.zoom)



    def __repr__(self):
        return f"Room: {self.room_type} #{self.room_number} | Capacity: {self.capacity} | Equipment: {self.equipment} | Zoom: {self.zoom}\n\t\tDates: {self.dates}\n"



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



class ScheduleCalendar:
    def __init__(self):
        self.buildings = []
        self.lock = asyncio.Lock()

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

    async def get_rooms_by_capacity(self, building_name: str, capacity_range: str, as_numbers: bool = False):
        """Get rooms filtered by capacity range"""
        rooms = []
        async with self.lock:
            for building in self.buildings:
                if building.building_name == building_name:
                    for room in building.rooms:
                        if self._room_matches_capacity(room, capacity_range):
                            if as_numbers:
                                rooms.append(room.room_number)
                            else:
                                rooms.append(room)
                    break
        return rooms

    def _room_matches_capacity(self, room: Room, capacity_range: str) -> bool:
        """Check if room matches capacity requirements"""
        if not room.capacity:
            return False

        if capacity_range == "small":
            return room.capacity < 30
        elif capacity_range == "medium":
            return 30 <= room.capacity <= 60
        elif capacity_range == "large":
            return room.capacity > 60
        return False

    async def get_room_by_number(self, building_name: str, room_number: str) -> Room:
        """Get room object by building and room number"""
        async with self.lock:
            for building in self.buildings:
                if building.building_name == building_name:
                    for room in building.rooms:
                        if room.room_number == room_number:
                            return room
        return None

    async def update_room_slot_status(self, building_name: str, room_number: str,
                                      target_date: date, time_slot: TimeSlot,
                                      is_free: bool, name: str = None):
        """Update room slot status in shared schedule"""
        async with self.lock:
            for building in self.buildings:
                if building.building_name == building_name:
                    for room in building.rooms:
                        if room.room_number == room_number:
                            for date_cell in room.dates:
                                if date_cell.date == target_date:
                                    for slot in date_cell.time_slots:
                                        if slot.start == time_slot.start and slot.end == time_slot.end:
                                            slot.status.is_free = is_free
                                            if name:
                                                slot.status.name = name
                                            return True
        return False

    async def update_schedule(self):
        async with self.lock:
            self.buildings.clear()
            # for building in schedule.buildings:
            #     self.buildings.append(copy.copy(building))
            await self.import_schedule()

    def __copy__(self):
        new_item = ScheduleCalendar()
        for building in self.buildings:
            new_item.buildings.append(copy.copy(building))
        return new_item

    async def import_schedule(self):
        # Current date and time in specific timezone
        current_datetime = datetime.now(UTC) + timedelta(hours=config.TIMEZONE)
        required_datetimes = [current_datetime]

        for i in range(config.DAYS_TO_SHOW):
            required_datetimes.append(
                current_datetime - timedelta(hours=current_datetime.hour, minutes=current_datetime.minute, seconds=current_datetime.second) + timedelta(days=i + 1)
            )

        # Fetch sheet metadata
        metadata = conn.spreadsheet.fetch_sheet_metadata(params={'fields': 'sheets.merges'})

        for worksheet in conn.spreadsheet.worksheets()[:1]:
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
                room_type = worksheet_data[2][i + 2]

                # List of equipment to specific room
                equipment = [k for k in worksheet_data[3][i + 2].split(", ") if k is not None]

                # Zoom support: bool
                zoom = "Zoom" in equipment
                if zoom:
                    equipment.remove("Zoom")

                # Room capacity (max)
                capacity = worksheet_data[4][i + 2] if worksheet_data[4][i + 2] == "" else int(worksheet_data[4][i + 2])

                # Creating room sample
                new_room = Room(
                    room_number=room_number,
                    room_type=room_type,
                    capacity=capacity,
                    equipment=equipment,
                    zoom=zoom
                )

                # Adding dates to room object
                for item in required_datetimes:
                    new_room.dates.append(
                        DateCell(item)
                    )

                # Update time slots available
                for k, date_cell in enumerate(new_room.dates):
                    weekday_no = date_cell.date.weekday()
                    for l, slot in enumerate(date_cell.time_slots):
                        # To locate exact row for each day and time slot
                        row = 9 * weekday_no + date_cell.get_time_slot_index(slot) + 5

                        # Here starts the cell parser of spreadsheet
                        # Get cell contents
                        cell_contents = worksheet_data[row][i + 2]
                        # Parse cell data
                        cell_data = self.__cell_parser(cell_contents, date_cell.date)
                        # Update slot status if cell is not free
                        if cell_data:
                            new_room.dates[k].time_slots[l].status.is_free = False
                            new_room.dates[k].time_slots[l].status.name = cell_data[0]
                            new_room.dates[k].time_slots[l].status.comment = cell_data[1]
                        else:
                            # check database for records if cell was booked
                            record = await check_if_booked(
                                building=building.address,
                                room=new_room.room_number,
                                date=date_cell.date,
                                start=slot.start,
                                end=slot.end
                            )

                            if record:
                                new_room.dates[k].time_slots[l].status.is_free = False
                                new_room.dates[k].time_slots[l].status.name = record.user.full_name if record.user else None
                                new_room.dates[k].time_slots[l].status.comment = None

                # Adding room to rooms list
                rooms.append(new_room)

            # Add rooms to building list
            building.add_rooms(rooms)
            # Add buildings to building list
            self.buildings.append(building)

    def __cell_parser(self, cell_contents: str, target_date: date):
        result = []
        current_cell = cell_contents

        # Divide cell contents by upper and lower weeks and decide with which one to proceed with
        if "---" in current_cell:
            m = re.match(r'(?s)\A(.*?)\r?\n?[ \t]*-+[ \t]*\r?\n?(.*)\Z', current_cell)
            if m and self.is_upper_week(target_date):
                current_cell = m.group(1).strip()
            elif m:
                current_cell = m.group(2).strip()

        if current_cell == "***":
            return result

        for line in current_cell.split("\n"):
            line_data = [k.strip() for k in line[1:].split("-")]

            if line == "***" or line == "":
                continue
            if line[0] == "!":
                exact_dates_pattern = r"^(?:\d{1,2}\.\d{1,2}\.\d{4})(?:,\s*\d{1,2}\.\d{1,2}\.\d{4})*$"
                exact_dates_raw = re.findall(exact_dates_pattern, line_data[0])
                exact_dates = []
                if exact_dates_raw:
                    for item in exact_dates_raw:
                        exact_dates.append(
                            datetime.strptime(item, "%d.%m.%Y").date()
                        )
                if target_date in exact_dates:
                    name = line_data[1]
                    comment = "-".join(line_data[2:]) if len(line_data) > 2 else None
                    result.extend([name, comment])
            elif line[0] == "#":
                if "с " in line and "по " in line:
                    pattern_from = r"с\s+(\d{2}\.\d{2}\.\d{4})"
                    pattern_to = r"по\s+(\d{2}\.\d{2}\.\d{4})"
                    start_date_raw = re.findall(pattern_from, line[1:])
                    end_date_raw = re.findall(pattern_to, line[1:])
                    if start_date_raw and end_date_raw:
                        start_date = datetime.strptime(start_date_raw[0], "%d.%m.%Y").date()
                        end_date = datetime.strptime(end_date_raw[0], "%d.%m.%Y").date()
                        date_diff = target_date - start_date
                        step = 14 if "---" in cell_contents else 7
                        if start_date <= target_date <= end_date and date_diff.days % step == 0:
                            name = line_data[1]
                            comment = "-".join(line_data[2:]) if len(line_data) > 2 else None
                            result = [name, comment]
                elif "с " in line:
                    pattern_from = r"с\s+(\d{2}\.\d{2}\.\d{4})"
                    start_date_raw = re.findall(pattern_from, line[1:])
                    if start_date_raw:
                        start_date = datetime.strptime(start_date_raw[0], "%d.%m.%Y").date()
                        if start_date <= target_date:
                            date_diff = target_date - start_date
                            step = 14 if "---" in cell_contents else 7
                            if date_diff.days % step == 0:
                                name = line_data[1]
                                comment = "-".join(line_data[2:]) if len(line_data) > 2 else None
                                result = [name, comment]
                elif "по " in line:
                    pattern_to = r"по\s+(\d{2}\.\d{2}\.\d{4})"
                    end_date_raw = re.findall(pattern_to, line[1:])
                    if end_date_raw:
                        end_date = datetime.strptime(end_date_raw[0], "%d.%m.%Y").date()
                        if end_date >= target_date:
                            date_diff = end_date - target_date
                            step = 14 if "---" in cell_contents else 7
                            if date_diff.days % step == 0:
                                name = line_data[1]
                                comment = "-".join(line_data[2:]) if len(line_data) > 2 else None
                                result = [name, comment]
            elif line[0] == "*":
                if "в " in line:
                    pattern_out = r'(?P<date>\d{1,2}\.\d{1,2}\.\d{4})\s+[вВ]\s+(?P<room>\d{3})\*{3}'
                    out_date_raw = re.findall(pattern_out, line[1:])
                    if out_date_raw:
                        out_date = datetime.strptime(out_date_raw[0][0], "%d.%m.%Y").date()
                        if out_date == target_date:
                            result = []

                elif "из " in line:
                    pattern_in = r'(?P<date>\d{1,2}\.\d{1,2}\.\d{4})\s+из\s+(?P<room>\d{3})\*{3}'
                    in_date_raw = re.findall(pattern_in, line[1:])
                    if in_date_raw:
                        in_date = datetime.strptime(in_date_raw[0][0], "%d.%m.%Y").date()
                        if in_date == target_date:
                            room = in_date_raw[0][1]
                            name = f"Перенос с аудитории {room}"
                            comment = None
                            result = [name, comment]
            elif line[0] == "$":
                name = line_data[0]
                comment = "-".join(line_data[1:]) if len(line_data) > 1 else None
                result = [name, comment]
        return result


    # Verify if week is upper (else it is lower)
    @staticmethod
    def is_upper_week(
            target_date: date,
            upper_week_date: date = config.UPPER_WEEK_START_DATE
    ) -> bool:
        """
        Parameters:
            target_date (datetime.date): The date to be checked if it is in an upper week
            upper_week_date (datetime.date): The date indicating start of upper week

        Returns:
            bool: 'True' if it is upper week, 'False' otherwise
        """

        # Weekday of upper week date
        upper_week_weekday = upper_week_date.weekday()

        # First day of the first upper week
        upper_week_first_date = upper_week_date - timedelta(days=upper_week_weekday)

        # calculate date difference between two dates + calculate weeks + identify if even or odd
        time_diff = target_date - upper_week_first_date
        return (time_diff.days // 7) % 2 == 0

    def __repr__(self):
        return f"Buildings: {self.buildings}"


if __name__ == "__main__":
    date_data = DateCell(datetime.now(UTC))
    print(date_data)
    new_date = copy.copy(date_data)
    print(new_date)
