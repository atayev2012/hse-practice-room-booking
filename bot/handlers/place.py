import copy
import random

from aiogram import Router, F
from aiogram.exceptions import DetailedAiogramError
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from bot.keyboards import (building_kb_place, rooms_kb, confirm_place_kb, main_menu_kb,
                           room_selection_type_kb, capacity_selection_kb, capacity_rooms_kb,
                           capacity_room_selection_type_kb)
from bot.utils import (render_place_card, kill_sticky_message)
from aiogram.fsm.state import StatesGroup, State
from bot.handlers.timepick import start_time_stage
from shared_data import SCHEDULE_SHARED

router = Router()


class Place(StatesGroup):
    building = State()
    room_selection_type = State()
    room_number = State()
    capacity_selection = State()
    capacity_room_selection_type = State()
    capacity_room_number = State()


# room booking start
@router.message(F.text == "📚 Забронировать аудиторию")
@router.message(Command("place"))
async def place_start(m: Message, state: FSMContext):
    print(f"Command to choose place entered")
    # Удаляем старую карточку «место», если была
    await kill_sticky_message(state, m, "place_msg_id")

    # Обнуляем выбор и создаём новую карточку
    await state.update_data(
        place_building=None,
        place_building_code=None,
        place_building_title=None,
        place_room=None,
        place_page=1,
        selection_type=None,
        capacity_range=None
    )
    msg = await m.answer(
        await render_place_card(await state.get_data(), review=False),
        reply_markup=await building_kb_place()
    )
    await state.update_data(place_msg_id=msg.message_id)
    await state.set_state(Place.building)


# list of rooms for a building
@router.callback_query(Place.building, F.data.startswith("bld:"))
async def place_choose_building(cq: CallbackQuery, state: FSMContext):
    code = cq.data.split(":", 1)[1]
    buildings_dict = await SCHEDULE_SHARED.get_buildings_dict()
    title = buildings_dict.get(code, "—")

    await state.update_data(
        place_building=title,
        place_building_code=code,
        place_building_title=title,
        place_room=None,
        place_page=1
    )

    # Ask for room selection type
    await cq.message.edit_text(
        text=f"📍 Выбран корпус: {title}\n\nВыберите способ выбора аудитории:",
        reply_markup=await room_selection_type_kb()
    )
    await state.set_state(Place.room_selection_type)
    await cq.answer()


# Room selection type handler
@router.callback_query(Place.room_selection_type, F.data.startswith("room_select:"))
async def room_selection_type_handler(cq: CallbackQuery, state: FSMContext):
    selection_type = cq.data.split(":", 1)[1]
    data = await state.get_data()
    building_code = data.get("place_building_code")

    await state.update_data(selection_type=selection_type)

    if selection_type == "by_number":
        # Show room numbers
        await cq.message.edit_text(
            text=f"📍 Выберите аудиторию в корпусе {data.get('place_building_title')}:",
            reply_markup=await rooms_kb(building_code, page=1)
        )
        await state.set_state(Place.room_number)

    elif selection_type == "any_room":
        # Ask for capacity requirement
        await cq.message.edit_text(
            text="📊 Выберите требуемую вместимость аудитории:",
            reply_markup=await capacity_selection_kb()
        )
        await state.set_state(Place.capacity_selection)

    elif selection_type == "back":
        await cq.message.edit_text(
            text=await render_place_card(await state.get_data(), review=False),
            reply_markup=await building_kb_place()
        )
        await state.set_state(Place.building)

    await cq.answer()


# Capacity selection handler
@router.callback_query(Place.capacity_selection, F.data.startswith("capacity:"))
async def capacity_selection_handler(cq: CallbackQuery, state: FSMContext):
    capacity_range = cq.data.split(":", 1)[1]
    data = await state.get_data()

    if capacity_range == "back":
        await cq.message.edit_text(
            text=f"📍 Выбран корпус: {data.get('place_building_title')}\n\nВыберите способ выбора аудитории:",
            reply_markup=await room_selection_type_kb()
        )
        await state.set_state(Place.room_selection_type)
    else:
        await state.update_data(capacity_range=capacity_range)

        # Ask for room selection method after capacity selection
        await cq.message.edit_text(
            text=f"📊 Выбрана вместимость: {capacity_range}\n\nВыберите способ выбора аудитории:",
            reply_markup=await capacity_room_selection_type_kb()
        )
        await state.set_state(Place.capacity_room_selection_type)

    await cq.answer()


# Capacity room selection type handler
@router.callback_query(Place.capacity_room_selection_type, F.data.startswith("capacity_room_select:"))
async def capacity_room_selection_type_handler(cq: CallbackQuery, state: FSMContext):
    selection_type = cq.data.split(":", 1)[1]
    data = await state.get_data()
    building_code = data.get("place_building_code")
    capacity_range = data.get("capacity_range")

    if selection_type == "any_room":
        # Find random room matching capacity
        matching_rooms = await SCHEDULE_SHARED.get_rooms_by_capacity(building_code, capacity_range)
        if matching_rooms:
            random_room = random.choice(matching_rooms)
            await state.update_data(place_room=random_room.room_number)

            # Show room details and proceed to time selection
            room_details = await get_room_details_text(random_room)
            await cq.message.edit_text(
                text=f"🎲 Случайно выбрана аудитория:\n\n{room_details}",
                reply_markup=await confirm_place_kb()
            )
        else:
            await cq.message.edit_text(
                text="❌ Не найдено аудиторий с выбранной вместимостью. Попробуйте другой вариант.",
                reply_markup=await capacity_room_selection_type_kb()
            )
            await cq.answer("Аудитории не найдены")
            return

    elif selection_type == "by_number":
        # Show room numbers matching capacity
        await cq.message.edit_text(
            text=f"📍 Выберите аудиторию в корпусе {data.get('place_building_title')} (вместимость: {capacity_range}):",
            reply_markup=await capacity_rooms_kb(building_code, capacity_range, page=1)
        )
        await state.set_state(Place.capacity_room_number)

    elif selection_type == "back":
        await cq.message.edit_text(
            text="📊 Выберите требуемую вместимость аудитории:",
            reply_markup=await capacity_selection_kb()
        )
        await state.set_state(Place.capacity_selection)

    await cq.answer()


# Choose room from capacity-filtered list
@router.callback_query(Place.capacity_room_number, F.data.startswith("room:"))
async def place_choose_capacity_room(cq: CallbackQuery, state: FSMContext):
    action = cq.data.split(":", 1)[1]
    data = await state.get_data()
    building_code = data.get("place_building_code")
    capacity_range = data.get("capacity_range")

    if action.startswith("page:"):
        try:
            page = int(action.split(":", 1)[1])
        except DetailedAiogramError as e:
            print(e)
            page = data.get("place_page", 1)
        await state.update_data(place_page=page)
        await cq.message.edit_reply_markup(
            reply_markup=await capacity_rooms_kb(building_code, capacity_range, page=page))
        await cq.answer()
        return

    if action == "noop":
        await cq.answer("Листайте ◀️ ▶️", show_alert=False)
        return

    if action == "back":
        await cq.message.edit_text(
            text=f"📊 Выбрана вместимость: {capacity_range}\n\nВыберите способ выбора аудитории:",
            reply_markup=await capacity_room_selection_type_kb()
        )
        await state.set_state(Place.capacity_room_selection_type)
        await cq.answer()
        return

    # Get room details and show confirmation
    room_obj = await SCHEDULE_SHARED.get_room_by_number(building_code, action)
    if room_obj:
        await state.update_data(place_room=action)
        room_details = await get_room_details_text(room_obj)

        await cq.message.edit_text(
            text=f"📍 Выбрана аудитория:\n\n{room_details}",
            reply_markup=await confirm_place_kb()
        )

    await cq.answer()


# Choose specific room number
@router.callback_query(Place.room_number, F.data.startswith("room:"))
async def place_choose_room(cq: CallbackQuery, state: FSMContext):
    action = cq.data.split(":", 1)[1]
    data = await state.get_data()
    code = data.get("place_building_code") or ""

    if action.startswith("page:"):
        try:
            page = int(action.split(":", 1)[1])
        except DetailedAiogramError as e:
            print(e)
            page = data.get("place_page", 1)
        await state.update_data(place_page=page)
        await cq.message.edit_reply_markup(reply_markup=await rooms_kb(code, page=page))
        await cq.answer()
        return

    if action == "noop":
        await cq.answer("Листайте ◀️ ▶️", show_alert=False)
        return

    if action == "back":
        await cq.message.edit_text(
            text=f"📍 Выбран корпус: {data.get('place_building_title')}\n\nВыберите способ выбора аудитории:",
            reply_markup=await room_selection_type_kb()
        )
        await state.set_state(Place.room_selection_type)
        await cq.answer()
        return

    # Get room details and show confirmation
    room_obj = await SCHEDULE_SHARED.get_room_by_number(code, action)
    if room_obj:
        await state.update_data(place_room=action)
        room_details = await get_room_details_text(room_obj)

        await cq.message.edit_text(
            text=f"📍 Выбрана аудитория:\n\n{room_details}",
            reply_markup=await confirm_place_kb()
        )

    await cq.answer()


async def get_room_details_text(room_obj) -> str:
    """Generate room details text"""
    zoom_status = "✅ Доступен" if room_obj.zoom else "❌ Не доступен"
    equipment_text = ", ".join(room_obj.equipment) if room_obj.equipment else "Нет"

    return (f"• Номер: {room_obj.room_number}\n"
            f"• Тип: {room_obj.room_type}\n"
            f"• Вместимость: {room_obj.capacity} человек\n"
            f"• Оборудование: {equipment_text}\n"
            f"• Zoom: {zoom_status}")


# change room after selection
@router.callback_query(F.data == "place:redo")
async def place_redo(cq: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selection_type = data.get("selection_type")

    if selection_type == "by_number":
        await cq.message.edit_text(
            text=f"📍 Выберите аудиторию в корпусе {data.get('place_building_title')}:",
            reply_markup=await rooms_kb(data.get("place_building_code"), page=1)
        )
        await state.set_state(Place.room_number)
    elif selection_type == "any_room":
        # Go back to capacity selection
        await cq.message.edit_text(
            text="📊 Выберите требуемую вместимость аудитории:",
            reply_markup=await capacity_selection_kb()
        )
        await state.set_state(Place.capacity_selection)
    else:
        await cq.message.edit_text(
            text=await render_place_card(await state.get_data(), review=False),
            reply_markup=await building_kb_place()
        )
        await state.set_state(Place.building)

    await cq.answer()


# accept and approve selected room
@router.callback_query(F.data == "place:ok")
async def place_ok(cq: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    building_name = data.get("place_building_code")
    room_number = data.get("place_room")

    if not building_name or not room_number:
        await cq.message.edit_text(
            text=await render_place_card(await state.get_data(), review=False),
            reply_markup=await building_kb_place()
        )
        await state.set_state(Place.building)
        await cq.answer()
        return

    try:
        # Get room details for final confirmation
        room_obj = await SCHEDULE_SHARED.get_room_by_number(building_name, room_number)
        room_details = await get_room_details_text(room_obj) if room_obj else ""

        await cq.message.edit_text(
            text=f"📍 Выбрана аудитория:\n\n{room_details}\n\n✅ Место подтверждено."
        )
    except DetailedAiogramError as e:
        print(e)

    # Get the room object directly from SHARED_SCHEDULE
    room_obj = await SCHEDULE_SHARED.get_room_by_number(building_name, room_number)

    if not room_obj:
        await cq.answer("❌ Ошибка: аудитория не найдена", show_alert=True)
        return

    # Use dates directly from the room object in SHARED_SCHEDULE
    # These are already the latest and include both schedule and database bookings
    final_date_required = []

    for room_date in room_obj.dates:
        # Create a copy of the date object
        date_copy = copy.copy(room_date)

        # Filter only free time slots
        date_copy.time_slots = [copy.copy(slot) for slot in room_date.time_slots if slot.status.is_free]

        # Only include dates that have available time slots
        if date_copy.time_slots:
            final_date_required.append(date_copy)

    await state.update_data(dates_required=final_date_required)

    # Check if any dates have available slots
    if not final_date_required:
        try:
            await cq.message.edit_text(
                text=f"📍 Выбрана аудитория:\n\n{room_details}\n\n❌ На ближайшие {len(room_obj.dates)} дней нет свободных слотов в этой аудитории. Выберите другую аудиторию.",
                reply_markup=await confirm_place_kb()
            )
        except DetailedAiogramError as e:
            print(e)
        await cq.answer()
        return

    # Moving onto next step of choosing time slots
    await start_time_stage(cq.message, state)
    await cq.answer()


@router.callback_query(F.data == "place:cancel")
async def place_cancel(cq: CallbackQuery, state: FSMContext):
    try:
        await cq.message.delete()
    except DetailedAiogramError as e:
        print(e)

    await state.update_data(
        place_building=None, place_building_code=None,
        place_building_title=None, place_room=None,
        place_msg_id=None, place_page=None,
        selection_type=None, capacity_range=None
    )
    await cq.message.answer("Выбор места отменён.", reply_markup=await main_menu_kb())
    await cq.answer()