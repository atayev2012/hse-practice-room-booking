import copy

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.exceptions import DetailedAiogramError
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from bot.utils import (render_time_card, send_booking_notification,
                       ensure_time_msg, kill_sticky_message)
from aiogram.fsm.state import StatesGroup, State
from bot.keyboards import day_kb, timeslots_kb, confirm_time_kb, main_menu_kb
from database.utils import get_records_by_building_room_date, is_room_recorded, create_record
from shared_data import SCHEDULE_SHARED

router = Router()


class TimePick(StatesGroup):
    day = State()
    slot = State()


@router.message(F.text == "🗓 Время")
@router.message(Command("time"))
async def time_start_cmd(m: Message, state: FSMContext):
    await start_time_stage(m, state)


@router.callback_query(TimePick.day, F.data.startswith("day:"))
async def pick_day(cq: CallbackQuery, state: FSMContext):
    key = cq.data.split(":", 1)[1]

    data = await state.get_data()
    building_code = data.get("place_building_code")
    room_number = data.get("place_room")

    # Get the room object directly from SHARED_SCHEDULE
    room_obj = await SCHEDULE_SHARED.get_room_by_number(building_code, room_number)

    if not room_obj:
        await cq.answer("❌ Ошибка: аудитория не найдена", show_alert=True)
        return

    # Find the date object in the room's schedule
    selected_date_obj = None
    for room_date in room_obj.dates:
        if room_date.weekday == key:
            selected_date_obj = copy.copy(room_date)
            break

    if selected_date_obj:
        # Keep ALL time slots (both free and booked) but mark them appropriately
        # The timeslots_kb will handle displaying booked slots with icons
        processed_slots = []
        for slot in selected_date_obj.time_slots:
            slot_copy = copy.copy(slot)
            processed_slots.append(slot_copy)

        selected_date_obj.time_slots = processed_slots

        await state.update_data(
            selected_date=selected_date_obj,
            time_day=selected_date_obj.weekday,
            time_date=selected_date_obj.date.strftime("%d.%m.%Y")
        )

        # Get room details for the message
        room_info = ""
        if room_obj:
            room_info = f"\n📍 Аудитория: {room_obj.room_number} ({room_obj.room_type})"

        # Show all time slots (free and booked) with appropriate icons
        await cq.message.edit_text(
            text=f"🗓 Выбран день: {selected_date_obj.weekday} ({selected_date_obj.date.strftime('%d.%m.%Y')}){room_info}\n\n"
                 f"✅ - свободно\n"
                 f"❌ - занято\n\n"
                 f"Выберите время:",
            reply_markup=await timeslots_kb(selected_date_obj.time_slots)
        )
        await state.set_state(TimePick.slot)
    else:
        await cq.answer("День не найден", show_alert=True)

    await cq.answer()


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
        # Find first available slot (only free ones)
        selected_date = state_data.get("selected_date")
        available_slots = [slot for slot in selected_date.time_slots if slot.status.is_free]
        if available_slots:
            selected_slot = available_slots[0]
        else:
            # No free slots available
            await cq.answer("❌ Нет доступных слотов на этот день. Выберите другой день.", show_alert=True)
            return
    else:
        # Find the selected slot
        slot_index = int(action) - 1
        selected_date = state_data.get("selected_date")
        if 0 <= slot_index < len(selected_date.time_slots):
            selected_slot = selected_date.time_slots[slot_index]
        else:
            await cq.answer("❌ Слот не найден", show_alert=True)
            return

    # Check if slot is available
    if selected_slot.status.is_free:
        await state.update_data(time_slot=selected_slot)

        # Get room details for confirmation
        building_code = state_data.get("place_building_code")
        room_number = state_data.get("place_room")
        room_obj = await SCHEDULE_SHARED.get_room_by_number(building_code, room_number)

        room_info = ""
        if room_obj:
            room_info = f"\n📍 Аудитория: {room_obj.room_number} ({room_obj.room_type})"

        confirmation_text = (f"🗓 Подтверждение бронирования:\n\n"
                             f"• День: {state_data.get('time_day')} ({state_data.get('time_date')}){room_info}\n"
                             f"• Время: {selected_slot.__repr__()}\n\n"
                             f"✅ Слот доступен для бронирования")

        await cq.message.edit_text(
            text=confirmation_text,
            reply_markup=await confirm_time_kb()
        )
    else:
        # Slot is booked - show detailed message with booker info and suggestions
        booker_name = selected_slot.status.name if selected_slot.status.name else "неизвестный пользователь"
        booker_comment = f"\nПричина: {selected_slot.status.comment}" if selected_slot.status.comment else ""

        error_message = (f"❌ Этот слот занят пользователем: {booker_name}{booker_comment}\n\n"
                         f"Пожалуйста, выберите:\n"
                         f"• Другой временной слот\n"
                         f"• Или другой день")

        await cq.answer(error_message, show_alert=True)

    await cq.answer()


@router.callback_query(F.data == "time:redo")
async def time_redo(cq: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    # Reload dates from SHARED_SCHEDULE for the redo operation
    building_code = data.get("place_building_code")
    room_number = data.get("place_room")
    room_obj = await SCHEDULE_SHARED.get_room_by_number(building_code, room_number)

    if room_obj:
        # Create fresh dates_required with latest data (including both free and booked)
        dates_required = []
        for room_date in room_obj.dates:
            date_copy = copy.copy(room_date)
            # Include all slots (free and booked) for display
            processed_slots = []
            for slot in room_date.time_slots:
                slot_copy = copy.copy(slot)
                processed_slots.append(slot_copy)
            date_copy.time_slots = processed_slots

            # Only include dates that have any slots (free or booked)
            if date_copy.time_slots:
                dates_required.append(date_copy)

        await state.update_data(dates_required=dates_required)

    await cq.message.edit_text(
        text=await render_time_card(data, review=False),
        reply_markup=await day_kb(data.get("dates_required"))
    )
    await state.set_state(TimePick.day)
    await cq.answer()


@router.callback_query(F.data == "time:ok")
async def time_ok(cq: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    if not await is_room_recorded(
            data.get("place_building_title"),
            data.get("place_room"),
            data.get("selected_date").date,
            data.get("time_slot").start,
            data.get("time_slot").end
    ):

        # Create booking record
        await create_record(
            cq.message.from_user.id,
            data.get("place_building_title"),
            data.get("place_room"),
            data.get("selected_date").date,
            data.get("time_slot").start,
            data.get("time_slot").end
        )

        # Update shared schedule
        await SCHEDULE_SHARED.update_room_slot_status(
            data.get("place_building_code"),
            data.get("place_room"),
            data.get("selected_date").date,
            data.get("time_slot"),
            is_free=False,
            name=cq.from_user.full_name
        )

        try:
            # Get room details for final message
            building_code = data.get("place_building_code")
            room_number = data.get("place_room")
            room_obj = await SCHEDULE_SHARED.get_room_by_number(building_code, room_number)

            room_info = ""
            if room_obj:
                room_info = f"\n📍 Аудитория: {room_obj.room_number} ({room_obj.room_type})"

            final_text = (f"✅ Бронирование подтверждено!\n\n"
                          f"• Корпус: {data.get('place_building_title')}{room_info}\n"
                          f"• День: {data.get('time_day')} ({data.get('time_date')})\n"
                          f"• Время: {data.get('time_slot').__repr__()}\n\n"
                          f"Запись сохранена в системе.")

            await cq.message.edit_text(text=final_text)

            await cq.message.answer(
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
        except DetailedAiogramError as e:
            print(e)

    else:
        try:
            await cq.message.edit_text(
                text=await render_time_card(data,
                                            review=True) + "\n\n❌ Время не подтверждено. Слот только что заняли. Выберите другой слот."
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

    # Load dates directly from SHARED_SCHEDULE
    building_code = data.get("place_building_code")
    room_number = data.get("place_room")
    room_obj = await SCHEDULE_SHARED.get_room_by_number(building_code, room_number)

    dates_required = []
    if room_obj:
        for room_date in room_obj.dates:
            date_copy = copy.copy(room_date)
            # Include all time slots (both free and booked) for display
            processed_slots = []
            for slot in room_date.time_slots:
                slot_copy = copy.copy(slot)
                processed_slots.append(slot_copy)
            date_copy.time_slots = processed_slots

            # Only include dates that have any slots
            if date_copy.time_slots:
                dates_required.append(date_copy)

        await state.update_data(dates_required=dates_required)

    await state.update_data(time_day=None, time_date=None, time_slot=None)

    # Get room details for the message
    room_info = ""
    if room_obj:
        room_info = f"\n📍 Аудитория: {room_obj.room_number} ({room_obj.room_type})"

    message_text = (f"🗓 Выберите день для бронирования{room_info}:\n\n"
                    f"Показаны все доступные дни с расписанием.")

    new_msg = await msg.bot.send_message(
        msg.chat.id,
        message_text,
        reply_markup=await day_kb(dates_required)
    )
    await state.update_data(time_msg_id=new_msg.message_id)
    await state.set_state(TimePick.day)