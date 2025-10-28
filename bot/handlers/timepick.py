import copy

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.exceptions import DetailedAiogramError
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from bot.utils import (render_time_card, parse_date_ddmmyyyy, send_booking_notification,
                       within_horizon, WEEKDAY_BY_INDEX, today_msk, WEEKDAY_INDEX,
                       nearest_non_past_weekday_date, fmt_date, WEEKDAY_TITLE, TIMESLOTS,
                       ensure_time_msg, kill_sticky_message)
from aiogram.fsm.state import StatesGroup, State
from bot.keyboards import day_kb, near_dates_kb, timeslots_kb, confirm_time_kb, main_menu_kb
from datetime import date, datetime, timedelta
from google.utils import DatesRequired, TimeSlot, TIME_SLOTS
from database.utils import get_records_by_building_room_date, is_room_recorded, create_record
from shared_data import SCHEDULE_SHARED

router = Router()

class TimePick(StatesGroup):
    day = State()
    date_input = State()
    slot = State()


@router.message(F.text == "🗓 Время")
@router.message(Command("time"))
async def time_start_cmd(m: Message, state: FSMContext):
    await start_time_stage(m, state)


# @router.callback_query(TimePick.day, F.data.startswith("pick:"))
# async def pick_specific_date(cq: CallbackQuery, state: FSMContext):
#     iso = cq.data.split(":", 1)[1]
#     print(f"Date picked = {iso}")
#     try:
#         d = date.fromisoformat(iso)
#     except DetailedAiogramError as e:
#         print(e)
#         await cq.answer("Неверная дата.", show_alert=True)
#         return
#
#     if not within_horizon(d):
#         await cq.answer("Можно бронировать только в ближайшие 3 дня (по МСК).", show_alert=True)
#         await cq.message.edit_text(
#             text="Выберите дату из доступных (ближайшие 3 дня по МСК):",
#             reply_markup=await near_dates_kb()
#         )
#         return
#
#     state_data = await state.get_data()
#     print(f"State = {state_data}")
#     time_slot_data = {"building": state_data["place_building_code"], "room": state_data["place_room"],
#                       "target_date": parse_date_ddmmyyyy(state_data["time_date"])}
#
#
#     wd_code = WEEKDAY_BY_INDEX[d.weekday()][0]
#     await state.update_data(time_day=wd_code, time_date=fmt_date(d))
#     await cq.message.edit_text(
#         text=await render_time_card(await state.get_data(), review=False),
#         reply_markup=await timeslots_kb(time_slot_data)
#     )
#     await state.set_state(TimePick.slot)
#     await cq.answer()


@router.callback_query(TimePick.day, F.data.startswith("day:"))
async def pick_day(cq: CallbackQuery, state: FSMContext):
    key = cq.data.split(":", 1)[1]

    data = await state.get_data()
    dates_required = data.get("dates_required")
    final_date_required = []
    for date_obj in dates_required:
        if date_obj.weekday == key:
            final_date_required = copy.copy(date_obj)
            await state.update_data(selected_date=final_date_required, time_day=date_obj.weekday, time_date=date_obj.date.strftime("%d.%m.%Y"))

    await cq.message.edit_text(
        text=await render_time_card(await state.get_data(), review=False),
        reply_markup=await timeslots_kb(final_date_required.time_slots)
    )
    await state.set_state(TimePick.slot)
    await cq.answer()


@router.callback_query(TimePick.date_input, F.data == "date:back")
async def date_back(cq: CallbackQuery, state: FSMContext):
    await cq.message.edit_text(
        text=await render_time_card(await state.get_data(), review=False),
        reply_markup=await day_kb()
    )
    await state.set_state(TimePick.day)
    await cq.answer()


# @router.message(TimePick.date_input)
# async def date_input_handler(m: Message, state: FSMContext):
#     s = m.text.strip()
#     d = parse_date_ddmmyyyy(s)
#     try:
#         await m.delete()
#     except DetailedAiogramError as e:
#         print(e)
#
#     if not d:
#         await m.bot.send_message(m.chat.id, "Неверный формат. Введите дату как ДД.ММ.ГГГГ (например, 02.10.2025).")
#         return
#
#     if not within_horizon(d):
#         await m.bot.send_message(
#             m.chat.id,
#             "Бронирование возможно только в ближайшие 3 дня (по МСК). Выберите одну из доступных дат:",
#             reply_markup=await near_dates_kb()
#         )
#         return
#
#     wd_code = WEEKDAY_BY_INDEX[d.weekday()][0]
#     await state.update_data(time_day=wd_code, time_date=fmt_date(d))
#
#     data = await state.get_data()
#     msg_id = data.get("time_msg_id") or await ensure_time_msg(state, m, review=False)
#
#     state_data = data
#     time_slot_data = {"building": state_data["place_building_code"], "room": state_data["place_room"],
#                       "target_date": parse_date_ddmmyyyy(state_data["time_date"])}
#     print(f"State = {state_data}")
#
#     await m.bot.edit_message_text(
#         chat_id=m.chat.id, message_id=msg_id,
#         text=await render_time_card(await state.get_data(), review=False),
#         reply_markup=await timeslots_kb(time_slot_data)
#     )
#     await state.set_state(TimePick.slot)


@router.callback_query(TimePick.slot, F.data.startswith("slot:"))
async def pick_slot(cq: CallbackQuery, state: FSMContext):
    action = cq.data.split(":", 1)[1]

    state_data = await state.get_data()
    if action == "back":
        await cq.message.edit_text(
            text=await render_time_card(await state.get_data(), review=False),
            reply_markup=await day_kb(state_data.get("dates_required"))
        )
        await state.set_state(TimePick.day)
        await cq.answer()
        return
    if action == "any":
        await state.update_data(time_slot="any")
    else:
        selected_slot = TimeSlot(start=TIME_SLOTS[int(action) - 1]["start"], end=TIME_SLOTS[int(action) - 1]["end"])
        await state.update_data(time_slot=selected_slot)

    await cq.message.edit_text(
        text=await render_time_card(await state.get_data(), review=True),
        reply_markup=await confirm_time_kb()
    )
    await cq.answer()

@router.callback_query(F.data == "time:redo")
async def time_redo(cq: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await cq.message.edit_text(
        text=await render_time_card(data, review=False),
        reply_markup=await day_kb(data.get("dates_required"))
    )
    await state.set_state(TimePick.day)
    await cq.answer()


@router.callback_query(F.data == "time:ok")
async def time_ok(cq: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    try:
        d = datetime.strptime(data.get("time_date",""), "%d.%m.%Y").date()
    except Exception:
        d = None
    # if not d or not within_horizon(d):
    #     await cq.message.edit_text(
    #         text="Выбранная дата больше недоступна (ограничение 3 дня по МСК). Выберите новую дату:",
    #         reply_markup=await near_dates_kb()
    #     )
    #     await state.set_state(TimePick.day)
    #     await cq.answer()
    #     return

    # TODO: check database for records, proceed if OK
    if not await is_room_recorded(
        data.get("place_building_title"),
        data.get("place_room"),
        data.get("selected_date").date,
        data.get("time_slot").start,
        data.get("time_slot").end
        ):

        await create_record(
            cq.message.from_user.id,
            data.get("place_building_title"),
            data.get("place_room"),
            data.get("selected_date").date,
            data.get("time_slot").start,
            data.get("time_slot").end
        )

        try:
            await cq.message.edit_text(
                text=await render_time_card(data, review=True) + "\n\n✅ Время подтверждено."
            )
        except DetailedAiogramError as e:
            print(e)

        day_title = data.get("time_day")
        date_part = f" ({data.get('time_date')})" if data.get("time_date") else ""
        slot_code = data.get("time_slot")
        slot_title = slot_code.__repr__()

        await cq.message.answer(
            f"Итог: {data.get('place_building_title') or '—'}, аудитория {data.get('place_room') or '—'}\n"
            f"День: {day_title}{date_part}\n"
            f"Время: {slot_title}\n\n"
            "Готово! Можно переходить к следующему шагу.",
            reply_markup=await main_menu_kb()
        )

        # Уведомление учебного отдела (с кликабельным ФИО)
        await send_booking_notification(
            cq.message.bot,
            cq.from_user.id,
            cq.from_user.full_name,
            data,
            cq.from_user.username
        )
        await cq.answer()

    else:
        try:
            await cq.message.edit_text(
                text=await render_time_card(data, review=True) + "\n\n❌ Время не подтверждено. Слот только что заняли. Выберите другой слот."
            )
        except DetailedAiogramError as e:
            print(e)


@router.callback_query(F.data == "time:cancel")
async def time_cancel(cq: CallbackQuery, state: FSMContext):
    try:
        await cq.message.delete()
    except DetailedAiogramError as e:
        print(e)

    await state.update_data(time_day=None, time_date=None, time_slot=None, time_msg_id=None)
    await cq.message.answer("Выбор времени отменён.", reply_markup=await main_menu_kb())
    await cq.answer()


async def start_time_stage(msg: Message, state: FSMContext):
    await kill_sticky_message(state, msg, "time_msg_id")

    data = await state.get_data()
    dates_required = data.get("dates_required")

    await state.update_data(time_day=None, time_date=None, time_slot=None)
    new_msg = await msg.bot.send_message(
        msg.chat.id,
        await render_time_card(await state.get_data(), review=False),
        reply_markup=await day_kb(dates_required)
    )
    await state.update_data(time_msg_id=new_msg.message_id)
    await state.set_state(TimePick.day)