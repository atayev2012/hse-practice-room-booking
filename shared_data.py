import asyncio
from google.schedule_parser import temp_data, load_and_parse
from google.API_connection import table
import copy

# global variable that stores schedule data
SCHEDULE_SHARED = {}

# lock for the global variable
LOCK = asyncio.Lock()

# async function to update the data from page every 2 minutes
async def update_schedule():
    global SCHEDULE_SHARED
    while True:
        await load_and_parse(table)
        async with LOCK:
            for building in temp_data.keys():
                SCHEDULE_SHARED[building] = {}
                for room in temp_data[building].keys():
                    SCHEDULE_SHARED[building][room] = {}
                    for category in temp_data[building][room].keys():
                        SCHEDULE_SHARED[building][room][category] = copy.deepcopy(temp_data[building][room][category])
        print("Schedule was updated")
        await asyncio.sleep(120)


# list of rooms
async def get_rooms_list(building_code: str) -> list:
    async with LOCK:
        rooms = list(SCHEDULE_SHARED.get(building_code).keys())
    return rooms


# get buildings by codes with their addresses if available
async def get_buildings_dict() -> dict:
    buildings = {
        "сормово": "Сормовское ш., 30",
        "родионова": "ул. Родионова, 136",
        "львовская": "ул. Львовская, 1в",
        "б.печерская": "ул. Большая Печерская, 25/12",
        "костина": "ул. Костина, 2",
    }
    async with LOCK:
        building_codes = list(SCHEDULE_SHARED.keys())

    result_buildings = {}
    for item in building_codes:
        building_code = item.lower()
        if buildings.get(building_code):
            result_buildings[building_code] = buildings.get(building_code)
        else:
            result_buildings[building_code] = item

    return result_buildings