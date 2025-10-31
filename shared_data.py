import asyncio
# from google.schedule_parser import temp_data, load_and_parse
# from google.connection import conn
# import copy
# from datetime import date
from google.schedule import ScheduleCalendar
from config import config


# global variable that stores schedule data
SCHEDULE_SHARED = ScheduleCalendar()


async def update_schedule():
    while True:
        await SCHEDULE_SHARED.update_schedule()
        await asyncio.sleep(config.SCHEDULE_UPDATE_INTERVAL * 60)

#
# # lock for the global variable
# LOCK = asyncio.Lock()
#
# # async function to update the data from page every 2 minutes
# async def update_schedule():
#     global SCHEDULE_SHARED
#     while True:
#         await load_and_parse(conn.spreadsheet)
#         async with LOCK:
#             SCHEDULE_SHARED = {}
#             for building in temp_data.keys():
#                 SCHEDULE_SHARED[building] = {}
#                 for room in temp_data[building].keys():
#                     SCHEDULE_SHARED[building][room] = {}
#                     for category in temp_data[building][room].keys():
#                         if category == "dates":
#                             SCHEDULE_SHARED[building][room][category] = {}
#                             for date_key in temp_data[building][room][category].keys():
#                                 SCHEDULE_SHARED[building][room][category][date_key] = {}
#                                 for time_slot in temp_data[building][room][category][date_key].keys():
#                                     SCHEDULE_SHARED[building][room][category][date_key][time_slot] = temp_data[building][room][category][date_key][time_slot]
#                         elif category == "capacity":
#                             SCHEDULE_SHARED[building][room][category] = temp_data[building][room][category]
#                         else:
#                             SCHEDULE_SHARED[building][room][category] = []
#                             for item in temp_data[building][room][category]:
#                                 SCHEDULE_SHARED[building][room][category].append(item)
#
#         print("Schedule was updated")
#         await asyncio.sleep(120)
#
#
# # list of rooms
# async def get_rooms_list(building_code: str) -> list:
#     async with LOCK:
#         rooms = list(SCHEDULE_SHARED.get(building_code).keys())
#     return rooms
#
#
# # get buildings by codes with their addresses if available
# async def get_buildings_dict() -> dict:
#     buildings = {
#         "сормово": "Сормовское ш., 30",
#         "родионова": "ул. Родионова, 136",
#         "львовская": "ул. Львовская, 1в",
#         "б.печерская": "ул. Большая Печерская, 25/12",
#         "костина": "ул. Костина, 2",
#     }
#     async with LOCK:
#         building_codes = list(SCHEDULE_SHARED.keys())
#
#     result_buildings = {}
#     for item in building_codes:
#         building_code = item.lower()
#         if buildings.get(building_code):
#             result_buildings[building_code] = buildings.get(building_code)
#         else:
#             result_buildings[building_code] = item
#
#     return result_buildings
#
# async def get_time_slots(building_code: str, room: str, target_date: date) -> list:
#     result_timeslots = []
#     async with LOCK:
#         print(SCHEDULE_SHARED.get(building_code).get(room).get("dates"))
#         print(f"Target date: {target_date} and type: {type(target_date)}")
#         print(SCHEDULE_SHARED.get(building_code).get(room).get("dates").get(target_date))
#         print(temp_data.get(building_code).get(room).get("dates").get(target_date))
#
#         # for timeslot in SCHEDULE_SHARED.get(building_code).get(room).get("dates").get(target_date).keys():
#         #     if SCHEDULE_SHARED.get(building_code).get(room).get("dates").get(target_date).get(timeslot) == 0:
#         #         result_timeslots.append(timeslot)
#
#     return result_timeslots