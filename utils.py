from datetime import datetime, date, UTC, timedelta, time
from config import config

# # GLOBAL VARIABLES
# WEEKDAYS_NAMES = {
#     0: "Понедельник",
#     1: "Вторник",
#     2: "Среда",
#     3: "Четверг",
#     4: "Пятница",
#     5: "Суббота",
#     6: "Воскресенье",
# }
#
# TIME_SLOTS = [
#     {"start": time(hour=8, minute=0), "end": time(hour=9, minute=20)},
#     {"start": time(hour=9, minute=30), "end": time(hour=10, minute=50)},
#     {"start": time(hour=11, minute=10), "end": time(hour=12, minute=30)},
#     {"start": time(hour=13, minute=0), "end": time(hour=14, minute=20)},
#     {"start": time(hour=14, minute=40), "end": time(hour=16, minute=0)},
#     {"start": time(hour=16, minute=20), "end": time(hour=17, minute=40)},
#     {"start": time(hour=18, minute=10), "end": time(hour=19, minute=30)},
#     {"start": time(hour=19, minute=40), "end": time(hour=21, minute=0)}
# ]
#
#
# class TimeSlot:
#     def __init__(self, start: time, end: time):
#         self.start = start
#         self.end = end
#
#     def __repr__(self):
#         return f"{self.start.strftime('%H:%M')}-{self.end.strftime('%H:%M')}"
#
#
# class ScheduleDate:
#     def __init__(self, target_datetime: datetime):
#         self.date = target_datetime.date()
#         self.time_slots = []
#         self.__set_weekday()
#         self.__set_time_slots(target_datetime)
#
#     def __set_weekday(self):
#         self.weekday = WEEKDAYS_NAMES.get(self.date.weekday())
#
#     def __set_time_slots(self, target_datetime: datetime):
#         # current time in specific time zone
#         current_datetime = datetime.now(UTC) + timedelta(hours=config.TIMEZONE)
#
#         for slot in TIME_SLOTS:
#             if slot.get("start") > current_datetime.time():
#                 self.time_slots.append(TimeSlot(slot.get("start"), slot.get("end")))
#
#     def __repr__(self):
#         return f"Date: {self.date.strftime('%d.%m.%Y')} {self.weekday} | Time Slots: {self.time_slots}"
#

# Schedule class containing
class Schedule:
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

            if target_datetime != current_datetime:
                target_datetime -= timedelta(hours=target_datetime.hour, minutes=target_datetime.minute)

            self.dates.append(ScheduleDate(target_datetime))

    def __repr__(self):
        return f"Schedule: {self.dates}"








# async def identify_dates() -> dict:
#     # current date and time as per moscow timezone
#     today_datetime_moscow = datetime.now(UTC) + timedelta(hours=config.TIMEZONE)
#
#     # if time already passed 19:00, then moveto the next day
#     if today_datetime_moscow.time() > time(hour=19, minute=40):
#         today_datetime_moscow += timedelta(hours=24 - today_datetime_moscow.hour)
#
#     result_dates = {}
#
#     for i in range(config.DAYS_TO_SHOW):
#         target_date = today_datetime_moscow.date() + timedelta(days=i)
#         result_dates[target_date] = {
#             "name": WEEKDAYS_NAMES[target_date.weekday()],
#             "time_slots_str": [],
#         }
#         for j, slot in enumerate(TIME_SLOTS):
#             if i == 0:
#                 if slot.get("start") > today_datetime_moscow.time():
#                     result_dates[target_date]["time_slots_str"].append(slot["str"])
#             else:
#                 result_dates[target_date]["time_slots_str"].append(slot["str"])
#
#     return result_dates


