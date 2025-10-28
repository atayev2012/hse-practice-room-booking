from aiogram.fsm.context import FSMContext
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, Message
)
from datetime import timedelta
from bot.utils import (today_msk, fmt_date_short, TIMESLOTS, ru_weekday_title, TIMESLOTS_LIST)
from shared_data import SCHEDULE_SHARED
from google.utils import TimeSlot
import random

# ========== profile handler keyboard markups ===========
async def status_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Преподаватель", callback_data="st:teacher")],
        [InlineKeyboardButton(text="Студент",       callback_data="st:student")],
        [InlineKeyboardButton(text="Адм. работник", callback_data="st:admin")],
    ])

async def confirm_inline_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Подтвердить ✅", callback_data="ok")],
        [InlineKeyboardButton(text="Изменить ❌",    callback_data="redo")],
    ])

async def edit_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Статус",  callback_data="chg:user_type")],
        [InlineKeyboardButton(text="ФИО",     callback_data="chg:full_name")],
        [InlineKeyboardButton(text="Телефон", callback_data="chg:phone")],
        [InlineKeyboardButton(text="Почта",   callback_data="chg:email")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="chg:back")],
    ])

async def profile_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Изменить статус",  callback_data="edit:user_type")],
        [InlineKeyboardButton(text="Изменить ФИО",     callback_data="edit:full_name")],
        [InlineKeyboardButton(text="Изменить телефон", callback_data="edit:phone")],
        [InlineKeyboardButton(text="Изменить почту",   callback_data="edit:email")],
        [InlineKeyboardButton(text="Сбросить профиль", callback_data="edit:reset")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="edit:back")],
    ])

async def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="ℹ️ Профиль")],
            [KeyboardButton(text="📚 Забронировать аудиторию")],
        ],
        resize_keyboard=True
    )

async def resend_code_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Отправить новый код", callback_data="resend_code")],
        [InlineKeyboardButton(text="✏️ Изменить email", callback_data="change_email")]
    ])

# =================================================================

# ========== place handler keyboard markups ===========
# keyboard with buildings
async def building_kb_place() -> InlineKeyboardMarkup:
    rows = []
    buildings_dict = await SCHEDULE_SHARED.get_buildings_dict()
    for building_name, building_address in buildings_dict.items():
        rows.append([InlineKeyboardButton(text=building_address, callback_data=f"bld:{building_name}")])
    rows.append([InlineKeyboardButton(text="Отмена", callback_data="place:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# keyboard with room numbers
async def rooms_kb(building_code: str, page: int = 1, per_page: int = 12) -> InlineKeyboardMarkup:
    rooms_list = await SCHEDULE_SHARED.get_rooms_list_by_building_name(building_code)
    total = len(rooms_list)
    random_room = 0
    if total > 1:
        random_room = random.randint(0, total - 1)
    if total == 0:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Любая", callback_data=f"room:{rooms_list[random_room]}")],
            [InlineKeyboardButton(text="⬅️ К корпусам", callback_data="room:back")],
        ])

    max_page = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, max_page))
    start = (page - 1) * per_page
    end = min(start + per_page, total)
    chunk = rooms_list[start:end]

    kb_rows = []
    row = []
    for i, r in enumerate(chunk, 1):
        row.append(InlineKeyboardButton(text=r, callback_data=f"room:{r}"))
        if i % 3 == 0:
            kb_rows.append(row)
            row = []
    if row:
        kb_rows.append(row)

    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(text="◀️", callback_data=f"room:page:{page-1}"))
    nav_row.append(InlineKeyboardButton(text=f"{page}/{max_page}", callback_data="room:noop"))
    if page < max_page:
        nav_row.append(InlineKeyboardButton(text="▶️", callback_data=f"room:page:{page+1}"))

    kb_rows.append([InlineKeyboardButton(text="Любая", callback_data=f"room:{rooms_list[random_room]}")])
    kb_rows.append(nav_row)
    kb_rows.append([InlineKeyboardButton(text="⬅️ К корпусам", callback_data="room:back")])

    return InlineKeyboardMarkup(inline_keyboard=kb_rows)


# confirmation keyboard
async def confirm_place_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Подтвердить ✅", callback_data="place:ok")],
        [InlineKeyboardButton(text="Изменить ❌",    callback_data="place:redo")],
    ])

# TODO: dates or days keyboard update as per available dates


# =========================================================

# ========== pick time handler keyboard markups ===========
# date or day selection
async def day_kb(dates_required) -> InlineKeyboardMarkup:
    rows = []

    for date_obj in dates_required:
        rows.append([
            InlineKeyboardButton(text=f"{date_obj.weekday} ({date_obj.date_to_str()})", callback_data=f"day:{date_obj.weekday}"),
        ])
    rows.extend([
        [InlineKeyboardButton(text="Отмена", callback_data="time:cancel")]
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)


async def near_dates_kb() -> InlineKeyboardMarkup:
    t = today_msk()
    options = [t + timedelta(days=i) for i in range(0, 4)]
    rows, row = [], []
    for d in options:
        label = f"{ru_weekday_title(d)} {fmt_date_short(d)}"
        row.append(InlineKeyboardButton(text=label, callback_data=f"pick:{d.isoformat()}"))
        if len(row) == 2:
            rows.append(row); row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="📅 Ввести дату", callback_data="day:date")])
    rows.append([InlineKeyboardButton(text="Отмена", callback_data="time:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def timeslots_kb(time_slots: list[TimeSlot]) -> InlineKeyboardMarkup:

    rows = []
    row = []
    random_slot = 0
    counter = 0
    print(time_slots)
    if time_slots:
        random_pos = random.randint(0, len(time_slots) - 1) if len(time_slots) > 1 else 0
        for slot in time_slots:
            ids, slot_str = slot.export_for_keyboard()
            if slot == time_slots[random_pos]:
                random_slot = ids
            row.append(
                InlineKeyboardButton(text=f"{slot_str}", callback_data=f"slot:{ids}")
            )
            counter += 1
            if counter % 2 == 0:
                rows.append(row)
                row = []

    if row:
        rows.append(row)

    rows.append([InlineKeyboardButton(text="⬅️ К дню", callback_data="slot:back")])
    if len(time_slots) > 1:
        rows[-1].append(InlineKeyboardButton(text="Любая пара", callback_data=f"slot:{random_slot}"))

    return InlineKeyboardMarkup(inline_keyboard=rows)

async def confirm_time_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Подтвердить ✅", callback_data="time:ok")],
        [InlineKeyboardButton(text="Изменить ❌",    callback_data="time:redo")],
    ])

# =========================================================








