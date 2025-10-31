import re, html, logging
from datetime import datetime, date, timedelta, UTC
from typing import Optional

from aiogram.fsm.context import FSMContext
from aiogram.exceptions import DetailedAiogramError

from database.utils import get_user
from config import config
from aiogram import Bot
from aiogram.types import Message
from aiogram.enums import ParseMode

from database.models import User

# =========== Profile handler utils ===========
# main form text for new and existing users
async def main_form(user: dict | User, review: bool = False, new_user: bool = True) -> str:
    if new_user and isinstance(user, dict):
        email_status = "✅ Подтверждён" if user.get('email_verified') else "❌ Не подтверждён"
        base = (
            "📝 Ваши данные\n\n"
            f"• Статус: {user.get('user_type') or '—'}\n"
            f"• ФИО: {user.get('full_name') or '—'}\n"
            # f"• Телефон: {user.get('phone') or '—'}\n"
            f"• Почта: {user.get('email') or '—'} ({email_status})\n\n"
        )
        tail = (
            "Проверьте корректность данных.\n"
            "Нажмите «Подтвердить» или «Изменить», чтобы исправить отдельный раздел."
            if review else
            "Заполните поля по очереди. После каждого шага это сообщение обновится."
        )

    else:
        email_status = "✅ Подтверждён" if getattr(user, 'email_verified', False) else "❌ Не подтверждён"
        base = ("С возвращением! Ваш профиль есть в нашей базе.\n\n"
        f"• Статус: {user.user_type}\n"
        f"• ФИО: {user.full_name}\n"
        # f"• Телефон: {user.phone}\n"
        f"• Почта: {user.email} ({email_status})\n\n"
        )
        tail = ("Нужно изменить — нажмите кнопку ниже 👇")

    return base + tail


# mapping user type from state after callback
async def map_user_type(code: str) -> str:
    user_type_dict = {
        "st:teacher": "Преподаватель",
        "st:student": "Студент",
        "st:admin":   "Административный работник"
    }
    return user_type_dict.get(code)

# ensure that after update updated main_form will be sent
async def ensure_form_msg(state: FSMContext, msg: Message, review: bool = False) -> int:
    data = await state.get_data()
    form_msg_id = data.get("form_msg_id")
    if form_msg_id:
        return form_msg_id
    payload = {
        "status": data.get("status"),
        "full_name": data.get("full_name"),
        # "phone": data.get("phone"),
        "email": data.get("email"),
    }
    new_msg = await msg.answer(await main_form(payload, review=review))
    await state.update_data(form_msg_id=new_msg.message_id)
    return new_msg.message_id

# delete prompt message
async def delete_prompt_if_any(state: FSMContext, msg: Message):
    data = await state.get_data()
    pid = data.get("prompt_msg_id")
    if pid:
        try:
            await msg.bot.delete_message(msg.chat.id, pid)
        except DetailedAiogramError as e:
            print(e)
        await state.update_data(prompt_msg_id=None)

PHONE_RE = re.compile(r"^(?:\+7|7|8)?\s?\(?\d{3}\)?[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}$")
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@(edu\.)?hse\.ru$")

# validation of phone number
async def phone_valid(txt: str) -> bool:
    return bool(PHONE_RE.match(txt.strip()))

# restructure the phone number in format of +7 (999) 999-99-99
async def restruct_phone(txt: str) -> str:
    txt = (txt.replace("-", "")
           .replace("+", "")
           .replace(" ", "")
           .replace("(", "")
           .replace(")", "")
           )
    if len(txt) > 10:
        if txt[0] == "8":
            txt = txt.replace("8", "")

        if txt[0] == "7":
            txt = txt.replace("7", "")

    new_phone = f"+7 ({txt[:3]}) {txt[3:6]}-{txt[6:8]}-{txt[8:]}"
    return new_phone


# validation of email
async def email_valid(txt: str) -> bool:
    return bool(EMAIL_RE.match(txt.strip()))

# verification of all fields to be filled
async def all_filled(data: dict) -> bool:
    return all(data.get(k) for k in ("user_type", "full_name", "email")) and data.get("email_verified")

#===============================================

# =========== Place handler utils ===========

async def kill_sticky_message(state: FSMContext, msg: Message, key: str):
    data = await state.get_data()
    mid = data.get(key)
    if mid:
        try:
            await msg.bot.delete_message(msg.chat.id, mid)
        except DetailedAiogramError as e:
            print(e)

        await state.update_data(**{key: None})


async def render_place_card(data: dict, review: bool = False) -> str:
    bld = data.get("place_building_title") or "—"
    room = data.get("place_room") or "—"
    base = (
        "📍 Определение места\n\n"
        f"• Адрес корпуса: {bld}\n"
        f"• № аудитории: {room}\n\n"
    )
    tail = ("Проверьте и подтвердите выбор." if review
            else "Сначала выберите корпус, затем аудиторию. Сообщение будет обновляться.")
    return base + tail



#===============================================

# =========== Time Pick handler utils ===========

async def nearest_non_past_weekday_date(wd_code: str, base: Optional[date] = None) -> date:
    if base is None:
        base = today_msk()
    target = WEEKDAY_INDEX[wd_code]
    delta = (target - base.weekday()) % 7
    return base + timedelta(days=delta)

async def ensure_time_msg(state: FSMContext, msg: Message, review: bool = False) -> int:
    data = await state.get_data()
    msg_id = data.get("time_msg_id")
    if msg_id:
        return msg_id
    new_msg = await msg.bot.send_message(msg.chat.id, await render_time_card(data, review=review))
    await state.update_data(time_msg_id=new_msg.message_id)
    return new_msg.message_id

async def send_booking_notification(bot: Bot, user_id: int, fallback_fullname: str, data: dict, username: Optional[str] = None):
    if not config.TELEGRAM_REPORT_CHAT_ID:
        return
    user = await get_user(user_id)
    status = user.user_type or data.get("user_type") or "Пользователь"
    fio_raw = user.full_name or data.get("full_name") or fallback_fullname

    fio_escaped = html.escape(fio_raw)
    if username:
        name_html = f'<a href="https://t.me/{username}">{fio_escaped}</a>'
    else:
        name_html = f'<a href="tg://user?id={user_id}">{fio_escaped}</a>'

    bld      = data.get("place_building_title") or "—"
    room     = data.get("place_room")
    date_str = data.get("selected_date").date.strftime("%d.%m.%Y")

    room_txt = f"аудиторию № {room}" if str(room).isdigit() else f"аудиторию {room}"

    time_txt = data.get("time_slot").__repr__() or "на указанную пару"

    text = (
        f"{status} {name_html} забронировал(а) в корпусе по адресу {bld} свободную {room_txt}, "
        f"{date_str}, {time_txt}."
    )
    try:
        await bot.send_message(config.TELEGRAM_REPORT_CHAT_ID, text, parse_mode=ParseMode.HTML)
    except DetailedAiogramError as e:
        print(e)
        logging.warning(f"Не удалось отправить уведомление о бронировании: {e}")

#===============================================

def slot_time_range_text(slot_code: Optional[str]) -> Optional[str]:
    if not slot_code:
        return None
    t = SLOT_TIMES.get(slot_code)
    if not t:
        return None
    start = t[0].replace(":", ".")
    end = t[1].replace(":", ".")
    return f"с {start} до {end}"


async def render_time_card(data: dict, review: bool = False) -> str:
    wd_title = data.get("time_day")
    date_str = data.get("time_date")
    day_line = "—"
    if wd_title and date_str:
        day_line = f"{wd_title} ({date_str})"
    elif wd_title:
        day_line = wd_title
    elif date_str:
        day_line = date_str

    if data.get("time_slot"):
        slot_title = data.get("time_slot").__repr__()
    else:
        slot_title = "—"
    base = (
        "🗓 Определение времени\n\n"
        f"• День: {day_line or '—'}\n"
        f"• Пара: {slot_title or '—'}\n\n"
    )

    # In case slots are empty
    if data.get("selected_date") and not data.get("selected_date").time_slots:
        tail = "Видимо свободных слотов на эту дату и время не осталось. Выберите другую дату или выберите другую аудиторию."
    elif not data.get("dates_required"):
        tail = "Видимо на ближайшие 3 дня в этой аудитории свободных слотов нет. Выберите другую аудиторию."
    else:
        tail = ("Проверьте и подтвердите выбор."
                if review else
                "Выберите день и время пары. Бронирование доступно на ближайшие 3 дня.")
    return base + tail



def fmt_date(d: date) -> str:
    return d.strftime("%d.%m.%Y")

def fmt_date_short(d: date) -> str:
    return d.strftime("%d.%m")

def ru_weekday_title(d: date) -> str:
    return WEEKDAY_BY_INDEX[d.weekday()][1]

def today_msk() -> date:
    return (datetime.now(UTC) + timedelta(hours=3)).date()

def within_horizon(d: date, horizon_days: int = 3) -> bool:
    t = today_msk()
    return t <= d <= (t + timedelta(days=horizon_days))


def parse_date_ddmmyyyy(s: str) -> Optional[date]:
    try:
        return datetime.strptime(s.strip(), "%d.%m.%Y").date()
    except Exception as e:
        print(e)
        return None


WEEKDAYS = [
    ("mon", "Понедельник"),
    ("tue", "Вторник"),
    ("wed", "Среда"),
    ("thu", "Четверг"),
    ("fri", "Пятница"),
    ("sat", "Суббота"),
    ("sun", "Воскресенье"),
]
WEEKDAY_INDEX = {"mon":0,"tue":1,"wed":2,"thu":3,"fri":4,"sat":5,"sun":6}
WEEKDAY_BY_INDEX = {
    0: ("mon", "Понедельник"),
    1: ("tue", "Вторник"),
    2: ("wed", "Среда"),
    3: ("thu", "Четверг"),
    4: ("fri", "Пятница"),
    5: ("sat", "Суббота"),
    6: ("sun", "Воскресенье"),
}
WEEKDAY_TITLE = {k: v for k, v in WEEKDAYS}

TIMESLOTS = {
    "1": "1 пара 08:00–09:20",
    "2": "2 пара 09:30–10:50",
    "3": "3 пара 11:10–12:30",
    "4": "4 пара 13:00–14:20",
    "5": "5 пара 14:40–16:00",
    "6": "6 пара 16:20–17:40",
    "7": "7 пара 18:10–19:30",
    "8": "8 пара 19:40–21:00",
}

SLOT_TIMES = {
    "1": ("08:00", "09:20"),
    "2": ("09:30", "10:50"),
    "3": ("11:10", "12:30"),
    "4": ("13:00", "14:20"),
    "5": ("14:40", "16:00"),
    "6": ("16:20", "17:40"),
    "7": ("18:10", "19:30"),
    "8": ("19:40", "21:00"),
}

TIMESLOTS_LIST = [
    "08:00–09:20",
    "09:30–10:50",
    "11:10–12:30",
    "13:00–14:20",
    "14:40–16:00",
    "16:20–17:40",
    "18:10–19:30",
    "19:40–21:00"
]
