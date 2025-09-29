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
        await asyncio.sleep(120)