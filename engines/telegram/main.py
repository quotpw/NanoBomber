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
bot_info = None
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
                pass
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


async def start_spam(message, rank, number: str, minutes: str = None) -> list:
    if (await sql.count_threads(message.chat.id)) >= rank.count_threads:
        return [
            False,
            f"Вы уже запустили <code>{rank.count_threads}</code> из <code>{rank.count_threads}</code> потоков.🤷‍♂️"
        ]

    if minutes is not None:
        if int(minutes) > rank.count_min:
            return [
                False,
                "Вы указали слишком много минут.\n<i>Вам доступно: </i><code>{rank.count_min}</code> минут."
            ]

    phone = Services.phone.Phone(number)

    if not phone.valid:
        return [
            False,
            "Вы указали неверный номер телефона."
        ]

    if minutes is not None:
        thread = threading.Thread(target=spam, args=[message, phone, int(minutes)])
        thread.start()

        return [
            True,
            thread
        ]

    return [
        True,
        phone.number
    ]


async def select_minuts_message(message, rank, phone):
    markup = types.InlineKeyboardMarkup()

    if rank.id == 1:
        markup.add(
            types.InlineKeyboardButton("5 минут", callback_data=f"re_spam::{phone}::5")
        )
    else:
        markup.add(
            types.InlineKeyboardButton("5 минут", callback_data=f"re_spam::{phone}::5"),
            types.InlineKeyboardButton("10 минут", callback_data=f"re_spam::{phone}::10"),
            types.InlineKeyboardButton("15 минут", callback_data=f"re_spam::{phone}::15")
        )

    if rank.id >= 2:
        markup.add(
            types.InlineKeyboardButton("Полчаса", callback_data=f"re_spam::{phone}::30"),
            types.InlineKeyboardButton("Час", callback_data=f"re_spam::{phone}::60")
        )
    if rank.id >= 3:
        markup.add(
            types.InlineKeyboardButton("1 Час, 30мин", callback_data=f"re_spam::{phone}::90"),
            types.InlineKeyboardButton("2 часа", callback_data=f"re_spam::{phone}::120")
        )
    if rank.id >= 4:
        markup.add(
            types.InlineKeyboardButton("2 часа, 30мин", callback_data=f"re_spam::{phone}::150"),
            types.InlineKeyboardButton("3 часа", callback_data=f"re_spam::{phone}::180")
        )
    if rank.id >= 5:
        markup.add(
            types.InlineKeyboardButton("4 Часа", callback_data=f"re_spam::{phone}::240"),
            types.InlineKeyboardButton("4 Часа, 30мин", callback_data=f"re_spam::{phone}::270"),
            types.InlineKeyboardButton("5 часов", callback_data=f"re_spam::{phone}::300")
        )

    await message.answer(
        f"<i>Номер телефона</i>: <code>{phone}</code>\n"
        f"<b>Выберите кол-во минут спама!</b>",
        reply_markup=markup
    )


@dp.message_handler(content_types=types.ContentType.CONTACT)
async def start_spam_handler_contact(message: types.Message):
    user = await sql.get_user(message.chat.id, message=message, bot=bot)
    rank = await sql.get_rank(user.rank_id)

    if not rank.access:
        return

    result = await start_spam(message, rank, message.contact.phone_number)
    if not result[0]:
        await message.answer(result[1])
    else:
        await select_minuts_message(message, rank, result[1])


@dp.message_handler(regexp="^[+]*\d{10,} \d{1,4}")
async def start_spam_handler(message: types.Message):
    user = await sql.get_user(message.chat.id, message=message, bot=bot)
    rank = await sql.get_rank(user.rank_id)

    if not rank.access:
        return

    bomb_info = re.findall("[+]*(\d{10,}) (\d{1,4})", message.text)

    if len(bomb_info) == 1:
        result = await start_spam(message, rank, bomb_info[0][0], bomb_info[0][1])
        if not result[0]:
            await message.answer(result[1])
    else:
        if (await sql.count_threads(message.chat.id)) >= rank.count_threads:
            await message.answer(
                "Вы уже запустили <code>{rank.count_threads}</code> из <code>{rank.count_threads}</code> потоков.🤷‍♂️"
            )
        elif (await sql.count_threads(message.chat.id)) + len(bomb_info) > rank.count_threads:
            ne_hvataet = (rank.count_threads - ((await sql.count_threads(message.chat.id)) + len(bomb_info))) * -1
            await message.answer(
                f"Увы, но вам не хватает <code>{ne_hvataet}</code> потоков, попробуйте указать меньше номеров!"
            )
        else:
            await message.answer("Произвожу поочередный запуск потоков!")
            for number in bomb_info:
                result = await start_spam(message, rank, number[0], number[1])
                if not result[0]:
                    await message.answer(result[1])
                await asyncio.sleep(0.2)


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


@dp.message_handler(content_types=types.ContentType.TEXT)
async def text_handler(message: types.Message):
    user = await sql.get_user(message.chat.id, message=message, bot=bot)
    rank = await sql.get_rank(user.rank_id)

    if message.text.replace('+', '').replace(' ', '').replace('-', '').replace('(', '').replace(')', '').isdigit():
        result = await start_spam(message, rank, re.sub("[^0-9]", "", message.text))
        if not result[0]:
            await message.answer(result[1])
        else:
            await select_minuts_message(message, rank, result[1])
        return

    promo = re.findall("^/start promo(.+)", message.text)
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
                "<b>ℹ️Есть несколько способов запуска спама:</b>\n"
                "\n"
                "\n"
                "<b>1)</b> Отправьте номер телефона жертвы:\n"
                "    - Допустимые форматы:\n"
                "        📞 <code>79000000228</code> - <i>просто номер телефона.</i>\n"
                "        📞 <code>+7 (970) 834-63-82</code> - <i>выебонский номер телефона.</i>\n"
                "        📞 <code>+7(999)7349364</code> - <i>еще один выебонский номер.</i>\n"
                "    - Далее предложат вам выбрать кол-во минут для спама.\n"
                "\n"
                "<b>2)</b> Отправьте контакт в телеграме:\n"
                "    - Допустимый формат:\n"
                "        ☎️ <code>Контакт</code> - <i>нажимаете на скрепку, далее контакты.</i>\n"
                "\n"
                "<b>3)</b> Отправьте номер и кол-во минут для спама:\n"
                "    - Допустимый формат:\n"
                "        📞 <code>79000012228 10</code> - <i>запуск спама на 10мин.</i>\n"
                "        📞 <code>380501334228 300</code> - <i>запуск спама на 5ч.</i>\n"
                "\n"
                "4) Отправьте список номеров и кол-во минут для спама:\n"
                "    - Допустимый формат:\n"
                "                <code>79000012228 10</code>\n"
                "                <code>380501334228 300</code>\n"
                "                <code>79180012468 24</code>\n"
                "                <code>79743073735 124</code>\n"
                "    - Далее бот проверит каждую строчку и запустит по потоку если это возможно.\n"
            )
        elif message.text == "👤Профиль👤":
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("Остановить все потоки", callback_data="stop_threads"))
            await message.answer_photo(
                open("img/profile.png", 'rb'),
                caption="⠀   <b>Ваш профиль:</b>\n"
                        f"⠀   <i>ID</i>: <code>{message.chat.id}</code>\n\n"
                        f"<b>== Информация о ранге ==</b>\n"
                        f"<i>Ранг</i>: <code>{rank.name}</code>\n"
                        f"<i>Максимум минут</i>: <code>{rank.count_min}</code>\n"
                        f"<i>Потоков</i>: <code>{await sql.count_threads(message.chat.id)}</code>/<code>"
                        f"{rank.count_threads}</code>\n"
                        f"<i>Подписка до</i>: <code>{subscribe_until(user.until)}</code>\n\n"
                        f"<b>== Реферальная система ==</b>\n"
                        f"<code>Вы получаете </code><b>{cfg.REF_PROC}%</b><code> от покупок ваших рефералов.</code>\n"
                        f'<i>Ваша ссылка</i>: '
                        f'<a href="https://t.me/{bot_info.username}?start=ref{message.chat.id}">Link</a>\n'
                        f"<i>Количество рефералов</i>: <code>{await sql.count_of_refers(message.chat.id)}</code>\n"
                        f"<i>Заработано денег</i>: <code>{user.balance}</code>rub\n\n"
                        f"<b>-</b> <i>“Для вывода обратитесь в поддержку”</i>",
                reply_markup=markup
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
    markup.add(types.InlineKeyboardButton("Обнуление баланса", callback_data=f"balance_null::{user.chatid}"))
    markup.add(types.InlineKeyboardButton("Вернуться ↩️", callback_data="admin"))

    rank = await sql.get_rank(user.rank_id)
    tg_info = await bot.get_chat(user.chatid)

    await bot.edit_message_caption(
        chat_id,
        message_id,
        caption=f"🆔: <code>{user.chatid}</code>\n\n"
                f"<b>== Информация о ранге ==</b>\n"
                f"<i>Ранг</i>: <code>{rank.name}</code>\n"
                f"<i>Максимум минут</i>: <code>{rank.count_min}</code>\n"
                f"<i>Потоков</i>: <code>{await sql.count_threads(user.chatid)}</code>/<code>"
                f"{rank.count_threads}</code>\n"
                f"<i>Подписка до</i>: <code>{subscribe_until(user.until)}</code>\n\n"
                f"<b>== Реферальная система ==</b>\n"
                f"<code>Вы получаете </code><b>{cfg.REF_PROC}%</b><code> от покупок ваших рефералов.</code>\n"
                f"<i>Количество рефералов</i>: <code>{await sql.count_of_refers(user.chatid)}</code>\n"
                f"<i>Заработано денег</i>: <code>{user.balance}</code>rub\n\n"
                f"<b>== Telegram-Info ==</b>\n"
                f"<i>Name</i>: {tg_info.full_name}\n"
                f"<i>Username</i>: @{tg_info.username}"
        ,
        reply_markup=markup
    )


async def show_select_rank(chat_id, message_id, return_callback, back):
    markup = types.InlineKeyboardMarkup()
    markup.add(*[
        types.InlineKeyboardButton(rank.name, callback_data=return_callback + f"::{rank.id}")
        for rank in await sql.get_ranks(sql.obj_factory)
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
    markup.add(
        types.InlineKeyboardButton("1 День", callback_data=return_callback + f"::{1}"),
        types.InlineKeyboardButton("7 Дней", callback_data=return_callback + f"::{7}"),
        types.InlineKeyboardButton("14 Дней", callback_data=return_callback + f"::{14}")
    )
    markup.add(
        types.InlineKeyboardButton("1 Месяц", callback_data=return_callback + f"::{int(1 * 30.417)}"),
        types.InlineKeyboardButton("3 Месяца", callback_data=return_callback + f"::{int(3 * 30.417)}"),
        types.InlineKeyboardButton("9 Месяцев", callback_data=return_callback + f"::{int(9 * 30.417)}")
    )
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
        result = await start_spam(query.message, rank, data_form[1], data_form[2])
        if not result[0]:
            await query.answer(result[1])
        await query.answer()

    elif rank.admin and data_form[0] == 'stop_all_threads':
        await sql.delete_threads()
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
        await query.answer()

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

    elif data_form[0] == 'stop_threads' and len(data_form) == 1:
        await sql.delete_user_threads(query.message.chat.id)
        await query.answer("Потоки остановлены!")
        try:
            await bot.delete_message(query.message.chat.id, query.message.message_id)
        except:
            pass

    elif rank.admin and data_form[0] == 'stop_threads' and len(data_form) == 2:
        await sql.delete_user_threads(data_form[1])
        await query.answer("Потоки пользователя остановлены!")
        await show_user_profile(query.message.chat.id, query.message.message_id, await sql.get_user(data_form[1]))

    elif rank.admin and data_form[0] == 'balance_null':
        await sql.balance_set(data_form[1], 0)
        await query.answer("Баланс успешно обнулен!")
        await show_user_profile(query.message.chat.id, query.message.message_id, await sql.get_user(data_form[1]))

    elif rank.admin and data_form[0] == 'promo':
        await show_promo(query.message.chat.id, query.message.message_id)
        await query.answer()

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
                f"https://t.me/nanobomber_bot?start=promo{promo}\n\n"
                f"<b>Будет активен до</b>: {subscribe_until(until)}"
            )
            await show_promo(query.message.chat.id, query.message.message_id)
        await query.answer()

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
    bot_info = loop.run_until_complete(bot.get_me())
    try:
        loop.run_until_complete(bot.send_message(1546285582, os.popen('ulimit -a').read()))
    except:
        pass
    loop.run_until_complete(sql.delete_threads())
    executor.start_polling(dp, loop=loop, skip_updates=True)
