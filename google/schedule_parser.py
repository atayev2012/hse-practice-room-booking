from gspread import Spreadsheet
from datetime import date, timedelta, datetime, timezone
from config import config
import re
import copy

temp_data = {}

async def load_and_parse(spreadsheet: Spreadsheet):
    global temp_data

    time_slots = [
        "08:00-09:20",
        "09:30-10:50",
        "11:10-12:30",
        "13:00-14:20",
        "14:40-16:00",
        "16:20-17:40",
        "18:10-19:30",
        "19:40-21:00"
    ]

    worksheets = spreadsheet.worksheets()
    # date period and whole list of dates
    start_date, end_date = await get_date_period(worksheets[0].acell("A1").value)
    dates_dict = await generate_list_of_dates(start_date, end_date)

    # Fetch sheet metadata
    metadata = spreadsheet.fetch_sheet_metadata(params={'fields': 'sheets.merges'})

    for i, worksheet in enumerate(worksheets):
        worksheet_title = worksheet.title.lower()
        if temp_data.get(worksheet_title) is None:
            # create key => building address Ex: 'Родионова', 'Б.Печерская', 'Костина', 'Львовская', 'Сормово'
            temp_data[worksheet_title] = {}

            # load all values
            worksheet_data = worksheet.get_all_values()

            # Copy data to empty merged cells
            for merges in metadata["sheets"]:
                for merge in merges["merges"]:
                    if merge.get("sheetId") == worksheet.id or (merge.get("sheetId") is None and worksheet.id ==0):
                        for i in range(merge["startRowIndex"], merge["endRowIndex"]):
                            for j in range(merge["startColumnIndex"], merge["endColumnIndex"]):
                                if not (i == merge["startRowIndex"] and j == merge["startColumnIndex"]):
                                    worksheet_data[i][j] = worksheet_data[merge["startRowIndex"]][merge["startColumnIndex"]]

            # start parsing
            for i, room in enumerate(worksheet_data[1][2:]):
                room = room.lower()
                if worksheet_data[2][i + 2] != "" or worksheet_data[3][i + 2] != "":
                    # Coworking title and Room Numbers entered wrong, that is the fix
                    if room == "коворкинг":
                        room = worksheet_data[2][i + 2]
                        worksheet_data[1][i + 2] = room
                        worksheet_data[2][i + 2] = ""

                    # add room number as key to specific worksheet (building)
                    temp_data[worksheet_title][room] = {}

                    # some equipment is divided by "\n" and some by "/"
                    if "/" in worksheet_data[2][i + 2]:
                        # changing "/" to "\n"
                        worksheet_data[2][i + 2] = worksheet_data[2][i + 2].replace("/", "\n")

                    # add list of equipment to specific room
                    temp_data[worksheet_title][room]["equipment"] = [k.strip().lower() for k in worksheet_data[2][i + 2].split("\n") if k.strip() != ""]

                    # add room capacity (max)
                    temp_data[worksheet_title][room]["capacity"] = worksheet_data[3][i + 2].lower()

                    # add dates
                    temp_data[worksheet_title][room]["dates"] = copy.deepcopy(dates_dict)

                    # update time slots of the specific cell
                    for cell_line in [l for l in range(4, 66) if (l - 4) % 9 < 8]:
                        cell_data = await parse_cell(worksheet_data[cell_line][i+2])
                        cell_weekday = (cell_line - 4) // 9
                        cell_time_slot = (cell_line - 4) % 9

                        if cell_data.get("upper_week") or cell_data.get("lower_week"):
                            if cell_data.get("upper_week"):
                                await update_by_cell_data(cell_data["upper_week"], cell_weekday,
                                                          time_slots[cell_time_slot],
                                                          worksheet_title, room, start_date, end_date, 1)

                            if cell_data.get("lower_week"):
                                await update_by_cell_data(cell_data["lower_week"], cell_weekday,
                                                          time_slots[cell_time_slot],
                                                          worksheet_title, room, start_date, end_date, 2)
                        else:
                            await update_by_cell_data(cell_data, cell_weekday, time_slots[cell_time_slot],
                                                      worksheet_title, room, start_date, end_date)


async def update_by_cell_data(
        cell_data: dict,
        cell_weekday,
        cell_time_slot,
        worksheet_title,
        room,
        start_date,
        end_date,
        week: int = 0
):
    global temp_data

    # for upper or lower week | 1 = upper | 2 = lower
    next_class_step = 14 if week != 0 else 7

    new_start_date = date(start_date.year, start_date.month, start_date.day)
    if week == 1:
        while not (new_start_date.weekday() == cell_weekday and await is_upper_week(new_start_date)):
            new_start_date = new_start_date + timedelta(days=1)
    elif week == 2:
        while not (new_start_date.weekday() == cell_weekday and not await is_upper_week(new_start_date)):
            new_start_date = new_start_date + timedelta(days=1)

    # if "all" key is true
    if cell_data.get("all"):
        temp_start_date = date(new_start_date.year, new_start_date.month, new_start_date.day)
        while temp_start_date <= end_date:
            temp_data[worksheet_title][room]["dates"][temp_start_date][cell_time_slot] = 1
            temp_start_date = temp_start_date + timedelta(days=next_class_step)

    # if there is a start date and possibly end date values
    if cell_data.get("start_date") and is_valid_date(cell_data["start_date"], "%d.%m"):
        # converting string to date type
        cell_data["start_date"] = datetime.strptime(
            f"{cell_data['start_date']}.{start_date.year}", "%d.%m.%Y").date()
        if cell_data["start_date"] < new_start_date:
            cell_data["start_date"] = date(new_start_date.year, new_start_date.month, new_start_date.day)
        if cell_data.get("end_date") and is_valid_date(cell_data["end_date"], "%d.%m"):
            cell_data["end_date"] = datetime.strptime(
                f"{cell_data['end_date']}.{end_date.year}", "%d.%m.%Y").date()
            if cell_data["end_date"] > end_date:
                cell_data["end_date"] = date(end_date.year, end_date.month, end_date.day)
        else:
            cell_data["end_date"] = date(end_date.year, end_date.month, end_date.day)

        while cell_data["end_date"] >= cell_data["start_date"]:
            temp_data[worksheet_title][room]["dates"][cell_data["start_date"]][cell_time_slot] = 1
            cell_data["start_date"] = cell_data["start_date"] + timedelta(days=next_class_step)

    # if only end date values
    if cell_data.get("start_date") is None:
        if cell_data.get("end_date") and is_valid_date(cell_data["end_date"], "%d.%m"):
            # converting string to date type
            cell_data["end_date"] = datetime.strptime(
                f"{cell_data['end_date']}.{end_date.year}", "%d.%m.%Y").date()
            if cell_data["end_date"] > end_date:
                cell_data["end_date"] = date(end_date.year, end_date.month, end_date.day)
            cell_data["start_date"] = date(new_start_date.year, new_start_date.month, new_start_date.day)

            while cell_data["end_date"] >= cell_data["start_date"]:
                temp_data[worksheet_title][room]["dates"][cell_data["start_date"]][
                    cell_time_slot] = 1
                cell_data["start_date"] = cell_data["start_date"] + timedelta(days=next_class_step)

    # free date values
    if cell_data.get("free_dates"):
        for free_date_str in cell_data["free_dates"]:
            # converting string to date type
            if is_valid_date(free_date_str, "%d.%m"):
                free_date = datetime.strptime(
                    f"{free_date_str}.{end_date.year}", "%d.%m.%Y").date()
                if new_start_date <= free_date <= end_date:
                    temp_data[worksheet_title][room]["dates"][free_date][cell_time_slot] = 0

    # booked dates
    if cell_data.get("booked_dates"):
        for booked_date_str in cell_data["booked_dates"]:
            # converting string to date type
            if is_valid_date(booked_date_str, "%d.%m"):
                booked_date = datetime.strptime(
                    f"{booked_date_str}.{end_date.year}", "%d.%m.%Y").date()
                if new_start_date <= booked_date <= end_date:
                    temp_data[worksheet_title][room]["dates"][booked_date][cell_time_slot] = 1





# Verify if week is upper (else it is lower)
async def is_upper_week(
        target_date: date,
        education_start_date: date = config.MODULES["1"]["start"],
        education_end_date: date = config.MODULES["4"]["end"]
) -> bool | None:
    """
    :param target_date: The date to be checked if it is in an upper week
    :param education_start_date: The date indicating start of education
    :param education_end_date: The date indicating end of education

    :return: 'True' if it is upper week, 'False' otherwise (None in case of date validation error)
    """
    if not isinstance(target_date, date) or target_date < education_start_date or target_date > education_end_date:
        return None

    education_start_weekday = education_start_date.weekday()

    # If first week starts with any day above 5 (Saturday) then move higher week to next week
    # else make higher week with current week by moving date to Monday of the same week
    if education_start_weekday > 5:
        first_week_start_date = education_start_date + timedelta(days=7 - education_start_weekday)
    else:
        first_week_start_date = education_start_date - timedelta(days=education_start_weekday)

    # calculate date difference between two dates + calculate weeks + identify if even or odd
    time_diff = target_date - first_week_start_date
    return (time_diff.days // 7) % 2 == 0


# get starting and ending dates for schedule
async def get_date_period(module_number_sheet: str, current_datetime: datetime = datetime.now(timezone.utc) + timedelta(hours=3)) -> list[date] | None:
    """
    :param module_number_sheet: The module number that was loaded from Google Sheet 1st cell
    :param current_datetime: Current date and time (in Moscow timezone [+03:00])

    :return: None if current_datetime is out of module range and List[start_date, end_date] otherwise
    """
    # get module number as string
    module_number = module_number_sheet.split(" ")[0]

    # if date is not in range of the specific module, then return None
    if current_datetime.date() > config.MODULES[module_number]["end"]:
        return None

    if current_datetime.date() < config.MODULES[module_number]["start"]:
        return [config.MODULES[module_number]["start"], config.MODULES[module_number]["end"]]

    return [current_datetime.date(), config.MODULES[module_number]["end"]]


async def generate_list_of_dates(start_date: date, end_date: date) -> dict[date, dict[str, int]]:
    """
    :param start_date: The start date of the list
    :param end_date: The end date of the list

    :return: Dates with timeslots from start_date to end_date => {date: {time_slot: 0}}
    """
    dates = {}
    current_date = date(start_date.year, start_date.month, start_date.day)
    while current_date <= end_date:
        dates[current_date] = {
            "08:00-09:20": 0,
            "09:30-10:50": 0,
            "11:10-12:30": 0,
            "13:00-14:20": 0,
            "14:40-16:00": 0,
            "16:20-17:40": 0,
            "18:10-19:30": 0,
            "19:40-21:00": 0
        }
        current_date = current_date + timedelta(days=1)

    return dates

async def parse_cell(sheet_cell: str) -> dict | None:
    """
    :param sheet_cell: The cell value from Google Sheet to be parsed
    :return: dict | None if sheet_cell is empty.
    Possible keys for dict: "upper_week", "lower_week", "start_date", "end_date", "booked_dates", "free_dates"
    """
    result = {}
    # check for lower and upper week
    if "--" in sheet_cell:
        # check what is in upper and lower weeks and recursively rerun parse_cell with found items
        m = re.match(r'(?s)\A(.*?)\r?\n?[ \t]*-+[ \t]*\r?\n?(.*)\Z', sheet_cell)
        if m:
            left = m.group(1).strip()
            right = m.group(2).strip()

            if left != "":
                result["upper_week"] = await parse_cell(m.group(1).strip())

            if right != "":
                result["lower_week"] = await parse_cell(m.group(2).strip())
        return result
    else:
        # if cell is empty, return none
        if sheet_cell == "" or sheet_cell == "***":
            return result

        # if cell has "в 123***", then make free date
        if "в " in sheet_cell and "***" in sheet_cell:
            pattern_in = r'(?P<date>\d{1,2}\.\d{1,2})\s+[вВ]\s+(?P<room>\d{3})\*{3}'
            free_dates = re.findall(pattern_in, sheet_cell)
            for item in free_dates:
                if result.get("free_dates") is None:
                    result["free_dates"] = []

                result["free_dates"].append(item[0])
                sheet_cell = sheet_cell.replace(f"{item[0]} в {item[1]}***", "").strip()

        # if cell has "из 123***", then make booked date
        if "из " in sheet_cell and "***" in sheet_cell:
            pattern_out = r'(?P<date>\d{1,2}\.\d{1,2})\s+из\s+(?P<room>\d{3})\*{3}'
            booked_dates = re.findall(pattern_out, sheet_cell)
            for item in booked_dates:
                if result.get("booked_dates") is None:
                    result["booked_dates"] = []

                result["booked_dates"].append(item[0])
                sheet_cell = sheet_cell.replace(f"{item[0]} из {item[1]}***", "").strip()

        # if cell has свобод
        if "свобод" in sheet_cell:
            pattern_free = r'(\d{1,2}\.\d{1,2})\s+свобод'
            sheet_cell = sheet_cell.replace("(", '')
            sheet_cell = sheet_cell.replace(")", '')
            free_dates = re.findall(pattern_free, sheet_cell)
            for item in free_dates:
                if result.get("free_dates") is None:
                    result["free_dates"] = []

                result["free_dates"].append(item)
                sheet_cell = sheet_cell.replace(f"{item} свобод", "").strip()

        # if cell has "с dd.mm", then make start date
        if "с " in sheet_cell:
            pattern_from = r"с\s+(\d{2}\.\d{2})"
            start_date = re.findall(pattern_from, sheet_cell)
            if start_date:
                result["start_date"] = start_date[0]

        # if cell has "до dd.mm", then make end date
        if "до " in sheet_cell:
            pattern_till = r"до\s+(\d{2}\.\d{2})"
            end_date = re.findall(pattern_till, sheet_cell)
            if end_date:
                result["end_date"] = end_date[0]


        # if start_date and end_date was not decided
        if result.get("start_date") is None and result.get("end_date") is None:
            pattern_start_end = r"(\d{1,2}\.\d{1,2})\s*-\s*(\d{1,2}\.\d{1,2})"
            start_end_dates = re.findall(pattern_start_end, sheet_cell)

            if start_end_dates:
                result["start_date"] = start_end_dates[0][0]
                result["end_date"] = start_end_dates[0][1]

        # if dates are written by comma
        pattern_dates = r"((?:\d{1,2},?)+)\.(\d{1,2})"
        dates = re.findall(pattern_dates, sheet_cell)

        if dates:
            if result.get("booked_dates") is None:
                result["booked_dates"] = []

            for item in dates:
                days = item[0].split(",")
                result["booked_dates"].extend([".".join([day, item[1]]) for day in days])
        else:
            if sheet_cell != "":
                result["all"] = True

        return result

def is_valid_date(date_string, date_format):
    """
    Checks if a given date string is a valid date according to the specified format.

    Args:
        date_string (str): The date string to validate.
        date_format (str): The expected format of the date string (e.g., "%Y-%m-%d").

    Returns:
        bool: True if the date is valid, False otherwise.
    """
    try:
        datetime.strptime(date_string, date_format)
        return True
    except ValueError:
        return False


if __name__ == '__main__':
    pass