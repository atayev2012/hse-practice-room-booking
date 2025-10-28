from aiogram import Router, F
from aiogram.exceptions import DetailedAiogramError
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from database.utils import get_user, update_user, create_user, delete_user
from bot.keyboards import status_kb, confirm_inline_kb, edit_menu_kb, profile_kb, main_menu_kb
from bot.utils import (main_form, map_user_type, ensure_form_msg, delete_prompt_if_any,
                       phone_valid, restruct_phone, email_valid, all_filled)
from email_ver.email_verification import Email

router = Router()

class UserState(StatesGroup):
    user_type = State() # user type: student, teacher, employee
    full_name = State() # full name: last name, first name, middle name
    phone = State() # phone number
    email = State() # email address
    email_verified = State()
    email_code = State()  # for entering verification code


# handler for /start command
@router.message(CommandStart())
async def cmd_start(m: Message, state: FSMContext):
    await state.clear()

    # check if user already exist
    user = await get_user(m.from_user.id)

    if user:
        await m.answer(
            await main_form(user=user, new_user=False),
            reply_markup=await main_menu_kb()
        )
    else:
        # set state to await for user_type
        await state.set_state(UserState.user_type)

        # clear data in state
        await state.update_data(user_type=None, full_name=None, phone=None, email=None)

        # send main form
        form = await m.answer(await main_form(await state.get_data()))
        await state.update_data(form_msg_id=form.message_id) # save message id

        # send prompt message with inline keyboard to choose user_type
        prompt = await m.answer("Здравствуйте! Укажите, пожалуйста, Ваш статус:", reply_markup=await status_kb())
        await state.update_data(prompt_msg_id=prompt.message_id) # save message id


# handler for callback query after selection of user_type (prefix st:)
@router.callback_query(UserState.user_type, F.data.startswith("st:"))
async def choose_status(cq: CallbackQuery, state: FSMContext):
    # get value of user_type by key with prefix "st:"
    user_type = await map_user_type(cq.data)
    # update user_type in state
    await state.update_data(user_type=user_type)
    # get latest state data
    data = await state.get_data()

    # if state data contains "profile_edit" key with value "user_type"
    # it means that it requires and update in database
    if data.get("profile_edit") == "user_type":
        user = await update_user(cq.from_user.id, **{"user_type": user_type})
        await state.update_data(profile_edit=None)

        # deleting message that contained keyboard of current callback action
        try:
            await cq.message.delete()
            await cq.message.bot.delete_message(cq.from_user.id, data.get("form_msg_id"))
        except DetailedAiogramError as e:
            print(e)

        await cq.message.answer(
            f"Статус обновлён ✅\n\nВаш профиль:\n"
            f"• Статус: {user.user_type}\n• ФИО: {user.full_name}\n• Телефон: {user.phone}\n• Почта: {user.email}",
            reply_markup=await profile_kb()
        )
    # if state data is on editing phase
    elif data.get("editing"):
        form_msg_id = await ensure_form_msg(state, cq.message, review=True)
        await cq.bot.edit_message_text(
            chat_id=cq.message.chat.id,
            message_id=form_msg_id,
            text=await main_form(await state.get_data(), review=True),
            reply_markup=await confirm_inline_kb()
        )

        try:
            await cq.message.delete()
        except DetailedAiogramError as e:
            print(e)

        await state.update_data(editing=False, edit_field=None)
        await state.set_state(None)

    else:
        form_msg_id = await ensure_form_msg(state, cq.message)
        await cq.bot.edit_message_text(
            chat_id=cq.message.chat.id, message_id=form_msg_id,
            text=await main_form(await state.get_data())
        )

        try:
            await cq.message.delete()
        except DetailedAiogramError as e:
            print(e)

        await state.update_data(prompt_msg_id=None)
        await state.set_state(UserState.full_name)
        prompt = await cq.message.answer("1.2. Укажите Ваше ФИО:")
        await state.update_data(prompt_msg_id=prompt.message_id)

# handler of full name state
@router.message(UserState.full_name)
async def got_full_name(m: Message, state: FSMContext):
    txt = m.text.strip()

    # if full name length is less than 5 characters
    if len(txt) < 5:
        try:
            await m.delete()
        except DetailedAiogramError as e:
            print(e)

        # delete prompt message
        await delete_prompt_if_any(state, m)

        # send new prompt message
        prompt = await m.bot.send_message(m.chat.id, "ФИО слишком короткое. Попробуйте снова:")
        await state.update_data(prompt_msg_id=prompt.message_id)
    else:
        # load latest data from state
        data = await state.get_data()

        if data.get("profile_edit") == "full_name":
            await update_user(m.from_user.id, **{"full_name": txt})
            await state.update_data(profile_edit=None)
            await delete_prompt_if_any(state, m)

            try:
                await m.delete()
                await m.bot.delete_message(m.from_user.id, data.get("form_msg_id"))
            except DetailedAiogramError as e:
                print(e)

            user = await get_user(m.from_user.id)
            await m.bot.send_message(
                m.chat.id,
                f"ФИО обновлено ✅\n\nВаш профиль:\n• Статус: {user.user_type}\n• ФИО: {user.full_name}\n• Телефон: {user.phone}\n• Почта: {user.email}",
                reply_markup=await profile_kb()
            )

        elif data.get("editing"):
            await state.update_data(full_name=txt)
            form_msg_id = await ensure_form_msg(state, m, review=True)
            await m.bot.edit_message_text(
                chat_id=m.chat.id, message_id=form_msg_id,
                text=await main_form(await state.get_data(), review=True),
                reply_markup=await confirm_inline_kb()
            )
            await delete_prompt_if_any(state, m)

            try:
                await m.delete()
            except DetailedAiogramError as e:
                print(e)

            await state.update_data(editing=False, edit_field=None)
            await state.set_state(None)
        else:
            await state.update_data(full_name=txt)
            form_msg_id = await ensure_form_msg(state, m)
            await m.bot.edit_message_text(
                chat_id=m.chat.id, message_id=form_msg_id,
                text=await main_form(await state.get_data())
            )
            await delete_prompt_if_any(state, m)

            try:
                await m.delete()
            except DetailedAiogramError as e:
                print(e)

            await state.set_state(UserState.phone)
            prompt = await m.bot.send_message(m.chat.id, "1.3. Укажите Ваш телефон (пример: +7 999 123-45-67):")
            await state.update_data(prompt_msg_id=prompt.message_id)


# handler of phone number state
@router.message(UserState.phone)
async def got_phone(m: Message, state: FSMContext):
    txt = m.text.strip()
    if not await phone_valid(txt):

        try:
            await m.delete()
        except DetailedAiogramError as e:
            print(e)

        await delete_prompt_if_any(state, m)
        prompt = await m.bot.send_message(m.chat.id, "Телефон не распознан. Пример: +7 999 123-45-67")
        await state.update_data(prompt_msg_id=prompt.message_id)
        return

    data = await state.get_data()

    if data.get("profile_edit") == "phone":
        new_phone = await restruct_phone(txt)
        await update_user(m.from_user.id, **{"phone": new_phone})
        await state.update_data(profile_edit=None)
        await delete_prompt_if_any(state, m)

        try:
            await m.delete()
            await m.bot.delete_message(m.from_user.id, data.get("form_msg_id"))
        except DetailedAiogramError as e:
            print(e)

        user = await get_user(m.from_user.id)
        await m.bot.send_message(
            m.chat.id,
            f"Телефон обновлён ✅\n\nВаш профиль:\n• Статус: {user.user_type}\n• ФИО: {user.full_name}\n• Телефон: {user.phone}\n• Почта: {user.email}",
            reply_markup=await profile_kb()
        )

    elif data.get("editing"):
        new_phone = await restruct_phone(txt)
        await state.update_data(phone=new_phone)
        form_msg_id = await ensure_form_msg(state, m, review=True)

        await m.bot.edit_message_text(
            chat_id=m.chat.id, message_id=form_msg_id,
            text=await main_form(await state.get_data(), review=True),
            reply_markup=await confirm_inline_kb()
        )

        await delete_prompt_if_any(state, m)

        try:
            await m.delete()
        except DetailedAiogramError as e:
            print(e)

        await state.update_data(editing=False, edit_field=None)
        await state.set_state(None)
    else:
        new_phone = await restruct_phone(txt)
        await state.update_data(phone=new_phone)
        form_msg_id = await ensure_form_msg(state, m)
        await m.bot.edit_message_text(
            chat_id=m.chat.id, message_id=form_msg_id,
            text=await main_form(await state.get_data())
        )
        await delete_prompt_if_any(state, m)

        try:
            await m.delete()
        except DetailedAiogramError as e:
            print(e)

        await state.set_state(UserState.email)
        prompt = await m.bot.send_message(m.chat.id, "1.4. Укажите корпоративную почту (например: ivanov@hse.ru):")
        await state.update_data(prompt_msg_id=prompt.message_id)

# handler of email
@router.message(UserState.email)
async def got_email(m: Message, state: FSMContext):
    print(f"Entered email field from {m.text}")
    txt = m.text.strip()
    if not await email_valid(txt):

        try:
            await m.delete()
        except DeprecationWarning as e:
            print(e)

        data = await state.get_data()
        await delete_prompt_if_any(state, m)

        if data.get("user_type"):
            accepted_domain = "@edu.hse.ru" if data.get("user_type") == "Студент" else "@hse.ru"
        else:
            user = await get_user(m.from_user.id)
            accepted_domain = "@edu.hse.ru" if user.user_type == "Студент" else "@hse.ru"

        prompt = await m.bot.send_message(m.chat.id, f"Почта некорректна!\nДопустимый домен: {accepted_domain}")
        await state.update_data(prompt_msg_id=prompt.message_id)
    else:

        data = await state.get_data()

        if data.get("profile_edit") == "email":
            await update_user(m.from_user.id, **{"email": txt.lower()})
            await state.update_data(profile_edit=None)
            await delete_prompt_if_any(state, m)

            try:
                await m.delete()
                await m.bot.delete_message(m.from_user.id, data.get("form_msg_id"))
            except DeprecationWarning as e:
                print(e)

            user = await get_user(m.from_user.id)
            await m.bot.send_message(
                m.chat.id,
                f"Почта обновлена ✅\n\nВаш профиль:\n• Статус: {user.user_type}\n• ФИО: {user.full_name}\n• Телефон: {user.phone}\n• Почта: {user.email}",
                reply_markup=await profile_kb()
            )
        else:
            await state.update_data(email=txt.lower())
            form_msg_id = await ensure_form_msg(state, m, review=True)
            await m.bot.edit_message_text(
                chat_id=m.chat.id, message_id=form_msg_id,
                text=await main_form(await state.get_data(), review=True),
                reply_markup=await confirm_inline_kb()
            )
            await delete_prompt_if_any(state, m)

            try:
                await m.delete()
            except DeprecationWarning as e:
                print(e)


@router.message(UserState.email_verified)
async def verify_email(m: Message, state: FSMContext):
    print(f"Entered email verification field")

    data = await state.get_data()

    email = Email(data.get("email"))
    await email.send_email()
    await state.update_data(email_verification_code=email.code)



# handler for changing data that was entered before (user_type, full_name, phone, email)
@router.callback_query(F.data == "redo")
async def show_change_menu(cq: CallbackQuery, state: FSMContext):
    form_msg_id = await ensure_form_msg(state, cq.message, review=True)
    await cq.bot.edit_message_text(
        chat_id=cq.message.chat.id, message_id=form_msg_id,
        text=await main_form(await state.get_data(), review=True) + "\n\nВыберите, что изменить:",
        reply_markup=await edit_menu_kb()
    )
    await cq.answer()


# handler for changing items in state
@router.callback_query(F.data.startswith("chg:"))
async def change_field(cq: CallbackQuery, state: FSMContext):
    what = cq.data.split(":", 1)[1]
    await state.update_data(editing=True, edit_field=what)
    await delete_prompt_if_any(state, cq.message)

    print("Entered change menu")

    if what == "user_type":
        await state.set_state(UserState.user_type)
        prompt = await cq.message.answer("Выберите новый статус:", reply_markup=await status_kb())
        await state.update_data(prompt_msg_id=prompt.message_id)
        print("Entered change user_type")
    elif what == "full_name":
        await state.set_state(UserState.full_name)
        prompt = await cq.message.answer("Введите новое ФИО:")
        await state.update_data(prompt_msg_id=prompt.message_id)
    elif what == "phone":
        await state.set_state(UserState.phone)
        prompt = await cq.message.answer("Введите новый телефон:")
        await state.update_data(prompt_msg_id=prompt.message_id)
    elif what == "email":
        await state.set_state(UserState.email)
        prompt = await cq.message.answer("Введите новую корпоративную почту:")
        await state.update_data(prompt_msg_id=prompt.message_id)
    elif what == "back":
        form_msg_id = await ensure_form_msg(state, cq.message, review=True)
        await cq.bot.edit_message_text(
            chat_id=cq.message.chat.id, message_id=form_msg_id,
            text=await main_form(await state.get_data(), review=True),
            reply_markup=await confirm_inline_kb()
        )
    await cq.answer()

# handler if all entered data is correct and approved by user
@router.callback_query(F.data == "ok")
async def confirm_ok(cq: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not await all_filled(data):
        await state.update_data(user_type=None, full_name=None, phone=None, email=None, editing=False, edit_field=None)
        form_msg_id = await ensure_form_msg(state, cq.message, review=False)
        await cq.bot.edit_message_text(
            chat_id=cq.message.chat.id, message_id=form_msg_id,
            text=await main_form(await state.get_data())
        )
        await state.set_state(UserState.user_type)
        prompt = await cq.message.answer("Данные неполные. Давайте начнём заново. Выберите статус:",
                                         reply_markup=await status_kb())
        await state.update_data(prompt_msg_id=prompt.message_id)
    else:


        await create_user(
            cq.from_user.id,
            data["full_name"],
            cq.from_user.username,
            data["phone"],
            data["email"],
            data["user_type"]
        )

        form_msg_id = data.get("form_msg_id")
        await state.clear()

        if form_msg_id:
            try:
                await cq.bot.edit_message_text(
                    chat_id=cq.message.chat.id, message_id=form_msg_id,
                    text=await main_form(data, review=True) + "\n\n✅ Заявка подтверждена и сохранена."
                )
            except DetailedAiogramError as e:
                print(e)
                await cq.message.answer("✅ Заявка подтверждена и сохранена.")
        else:
            await cq.message.answer("✅ Заявка подтверждена и сохранена.")

        await cq.message.answer("Готово. Чем займёмся дальше?", reply_markup=await main_menu_kb())


# handler to edit data in state
@router.callback_query(F.data.startswith("edit:"))
async def edit_profile(cq: CallbackQuery, state: FSMContext):
    action = cq.data.split(":", 1)[1]
    uid = cq.from_user.id

    await delete_prompt_if_any(state, cq.message)

    if action == "reset":
        await delete_user(uid)
        await state.clear()
        try:
            await cq.message.edit_text("Профиль удалён. Нажмите /start для повторной регистрации.")
        except DetailedAiogramError as e:
            print(e)

        await cq.answer("Профиль сброшен")
    else:
        if action == "user_type":
            await state.update_data(profile_edit="user_type")
            await state.set_state(UserState.user_type)
            await state.update_data(form_msg_id=cq.message.message_id)
            await cq.message.edit_reply_markup(str(cq.message.message_id), reply_markup=None)
            prompt = await cq.message.answer("Выберите новый статус:", reply_markup=await status_kb())
            await state.update_data(prompt_msg_id=prompt.message_id)

        elif action == "full_name":
            await state.update_data(profile_edit="full_name")
            await state.set_state(UserState.full_name)
            await state.update_data(form_msg_id=cq.message.message_id)
            await cq.message.edit_reply_markup(str(cq.message.message_id), reply_markup=None)
            prompt = await cq.message.answer("Введите новое ФИО:")
            await state.update_data(prompt_msg_id=prompt.message_id)

        elif action == "phone":
            await state.update_data(profile_edit="phone")
            await state.set_state(UserState.phone)
            await state.update_data(form_msg_id=cq.message.message_id)
            await cq.message.edit_reply_markup(str(cq.message.message_id), reply_markup=None)
            prompt = await cq.message.answer("Введите новый телефон:")
            await state.update_data(prompt_msg_id=prompt.message_id)

        elif action == "email":
            await state.update_data(profile_edit="email")
            await state.set_state(UserState.email)
            await state.update_data(form_msg_id=cq.message.message_id)
            await cq.message.edit_reply_markup(str(cq.message.message_id), reply_markup=None)
            prompt = await cq.message.answer("Введите новую корпоративную почту:")
            await state.update_data(prompt_msg_id=prompt.message_id)

        elif action == "back":
            user = await get_user(uid)

            # deleting message that contained keyboard of current callback action
            try:
                await cq.message.delete()
            except DetailedAiogramError as e:
                print(e)

            await cq.message.answer(await main_form(user))



            # data = await state.get_data()
            # # await delete_prompt_if_any(state, data[""])
            # await state.update_data(profile_edit=None)
            prompt = await cq.message.answer("Чем займёмся дальше?", reply_markup=await main_menu_kb())
            await state.clear()
            # await state.update_data(prompt_msg_id=prompt.message_id)

        await cq.answer()


# handler to show profile buttons
@router.message(F.text == "ℹ️ Профиль")
async def show_profile_btn(m: Message):
    user = await get_user(m.from_user.id)
    if not user:
        await m.answer("Профиль не найден. Нажмите /start для регистрации.")
    else:
        await m.answer(
            f"Ваш профиль:\n• Статус: {user.user_type}\n• ФИО: {user.full_name}"
            f"\n• Телефон: {user.phone}\n• Почта: {user.email}",
            reply_markup=await profile_kb()
        )

# handler of profile command
@router.message(Command("profile"))
async def show_profile_cmd(m: Message):
    await show_profile_btn(m)

@router.message(Command("cancel"))
async def cmd_cancel(m: Message, state: FSMContext):
    await delete_prompt_if_any(state, m)
    try:
        await m.delete()
    except DetailedAiogramError as e:
        print(e)
    await state.clear()
    await m.answer("Ок, начнём заново. Нажмите /start, чтобы повторить.", reply_markup=await main_menu_kb())
