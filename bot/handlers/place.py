from aiogram import Router, F
from aiogram.exceptions import DetailedAiogramError
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from bot.keyboards import building_kb_place, rooms_kb, confirm_place_kb, main_menu_kb, day_kb
from bot.utils import (render_place_card, kill_sticky_message, start_time_stage)
from aiogram.fsm.state import StatesGroup, State
from shared_data import get_buildings_dict


router = Router()

class Place(StatesGroup):
    building = State()
    room = State()

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
        place_page=1
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
    buildings_dict = await get_buildings_dict()
    title = buildings_dict.get(code, "—")

    await state.update_data(
        place_building=title,
        place_building_code=code,
        place_building_title=title,
        place_room=None,
        place_page=1
    )

    await cq.message.edit_text(
        text= await render_place_card(await state.get_data(), review=False),
        reply_markup=await rooms_kb(code, page=1)
    )
    await state.set_state(Place.room)
    await cq.answer()


# choose room and change pages of rooms
@router.callback_query(Place.room, F.data.startswith("room:"))
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
            text= await render_place_card(await state.get_data(), review=False),
            reply_markup=await building_kb_place()
        )
        await state.set_state(Place.building)
        await cq.answer()
        return

    if action == "any":
        await state.update_data(place_room="Любая")
    else:
        await state.update_data(place_room=action)

    await cq.message.edit_text(
        text= await render_place_card(await state.get_data(), review=True),
        reply_markup=await confirm_place_kb()
    )
    await cq.answer()

# change room after selection
@router.callback_query(F.data == "place:redo")
async def place_redo(cq: CallbackQuery, state: FSMContext):
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
    bld  = data.get("place_building_title")
    room = data.get("place_room")

    if not bld or not room:
        await cq.message.edit_text(
            text=await render_place_card(await state.get_data(), review=False),
            reply_markup=await building_kb_place()
        )
        await state.set_state(Place.building)
        await cq.answer()
        return

    try:
        await cq.message.edit_text(
            text=await render_place_card(data, review=True) + "\n\n✅ Место подтверждено."
        )
    except DetailedAiogramError as e:
        print(e)

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
        place_msg_id=None, place_page=None
    )
    await cq.message.answer("Выбор места отменён.", reply_markup=await main_menu_kb())
    await cq.answer()