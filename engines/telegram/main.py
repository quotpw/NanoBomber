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

from aiogram.types import ContentTypes
from aiogram_broadcaster import MessageBroadcaster

from func import *
import Services
import Services.proxoid

from aiogram import Bot, Dispatcher, executor, types
import config_file as cfg
from _sql import Sql

os.chdir(os.path.dirname(os.path.realpath(__file__)))

if os.name == 'nt':  # If os == Шindows
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())  # fix for "Asyncio Event Loop is Closed"

logging.basicConfig(level=logging.WARNING)

sql = Sql(cfg.DB_NAME)
bot = Bot(token=cfg.TG_TOKEN, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot)


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
    await sql.create_thread(thread_id, message.chat.id)

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Остановить⛔️", callback_data=f"stop_thr::{thread_id}"))
    spam_info_msg = await message.reply(
        "<b>Спам успешно запущен!</b>\n\n"
        f"<b>Жертва</b>:  <code>{phone.number}</code>\n"
        f"<b>Количество минут спама</b>:  <code>{minutes}</code>\n"
        f"<b>Закончит примерно в</b>   <i>~</i> "
        f"<code>{stamp_to_date(alive_until, return_time=True)}</code><i>msk</i>",
        reply_markup=markup
    )

    requester = Services.Services(phone)
    await requester.async_load_from_sqlite3(cfg.DB_NAME, 'services')
    while (await sql.thread_alive(thread_id)) and time.time() < alive_until:
        proxy = Services.proxoid.proxy.rotated_proxy  # None

        # while proxy is None:
        #     temp_proxy = Services.proxoid.proxy.rotated_proxy
        #     try:
        #         fut = asyncio.open_connection(temp_proxy.ip, int(temp_proxy.port))  # proxy.ip, proxy.port
        #         await asyncio.wait_for(fut, timeout=2)
        #         proxy = temp_proxy
        #     except:
        #         temp_proxy.report()
        # print(proxy)

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


@dp.message_handler(regexp="^[+]*\d{10,} \d{1,3}")
async def start_spam_handler(message: types.Message):
    user = await sql.get_user(message.chat.id)
    rank = await sql.get_rank(user.rank_id)

    if not rank.access:
        return

    if (await sql.count_threads(message.chat.id)) >= rank.count_threads:
        await message.answer(f"Вы уже запустили <code>{rank.count_threads}</code> "
                             f"из <code>{rank.count_threads}</code> потоков.🤷‍♂️")
        return

    bomb_info = re.findall("^[+]*(\d{10,}) (\d{1,3})", message.text)[0]

    if int(bomb_info[1]) > rank.count_min:
        await message.answer("Вы указали слишком много минут.\n"
                             f"<i>Вам доступно: </i><code>{rank.count_min}</code> минут.")
        return

    phone = Services.phone.Phone(bomb_info[0])

    if not phone.valid:
        await message.answer("Вы указали неверный номер телефона.")
        return

    threading.Thread(target=spam, args=[message, phone, int(bomb_info[1])]).start()


@dp.message_handler(commands=['stats'])
async def stats_handler(message: types.Message):
    user = await sql.get_user(message.chat.id)
    rank = await sql.get_rank(user.rank_id)

    if rank.admin:
        await message.answer(
            f"<b>Пользователей всего</b>: <code>{await sql.count_of_users()}</code>\n\n" +
            ("\n".join([f"{_rank['rank_id']}) {_rank['name']}: <code>{_rank['count']}</code>" for _rank in
                        await sql.get_rank_stats()])) +
            F"\n\n<b>Запущеных потоков</b>: <code>{await sql.count_threads()}</code>"
        )


@dp.message_handler(regexp='^/set_rank \d+ \d+')
async def change_rank_handler(message: types.Message):
    user = await sql.get_user(message.chat.id)
    rank = await sql.get_rank(user.rank_id)

    if rank.admin:
        args = message.text.split()[1:]

        selected_rank = await sql.get_rank(args[1], False)
        if selected_rank:
            selected_rank = selected_rank[0]

            await sql.change_rank(args[0], selected_rank.rank_id)

            try:
                await bot.send_message(int(args[0]), f'Ваш ранг был сменен на {selected_rank.name}.\n'
                                                     f'Нажмите /start чтоб обновить клавиатуру.')
            except:
                pass

            await message.answer(f"Ранг пользователя был изменен на {selected_rank.name}.")
        else:
            await message.reply("Извини, но такого ранга нету.")


@dp.message_handler(regexp='^/set_expire \d+ \d+')
async def set_expire_handler(message: types.Message):
    user = await sql.get_user(message.chat.id)
    rank = await sql.get_rank(user.rank_id)

    if rank.admin:
        args = message.text.split()[1:]

        await sql.change_expire(args[0], args[1])

        until = subscribe_until(int(args[1]))
        try:
            await bot.send_message(
                int(args[0]),
                f'Ваша подписка была продлена до {until}'
            )
        except:
            pass

        await message.answer(f"Подписка пользователя была продлена до {until}")


@dp.message_handler(commands=['stop_threads'])
async def stop_threads_handler(message: types.Message):
    user = await sql.get_user(message.chat.id)
    rank = await sql.get_rank(user.rank_id)

    if rank.admin:
        await sql.delete_threads()
        await message.answer("Успешно остановлены все потоки!")


@dp.message_handler(regexp='^/gen_promo \d+ \d+')
async def promo_handler(message: types.Message):
    user = await sql.get_user(message.chat.id)
    rank = await sql.get_rank(user.rank_id)

    if rank.admin:
        args = message.text.split()[1:]
        _rank = await sql.get_rank(args[0], False)
        if _rank:
            uid = await sql.create_promo(str(uuid.uuid4()).split('-')[0], _rank[0].rank_id, args[1])
            await message.answer(f"Ваш промокод на подписку {_rank[0].name} создан:\n"
                                 f"https://t.me/nanobomber_bot?start={uid}\n\n"
                                 f"<b>Подписка будет активна до</b>: {subscribe_until(int(args[1]))}")
        else:
            await message.answer("Ранга не существует.")


@dp.message_handler(regexp='^/ban \d+')
async def ban_handler(message: types.Message):
    user = await sql.get_user(message.chat.id)
    rank = await sql.get_rank(user.rank_id)

    if rank.admin:
        args = message.text.split()[1:]
        await sql.change_rank(args[0], -1, 0)
        try:
            await bot.send_message(args[0], "Чучело, тя забанили нахуй, соси хуец - молодец💋")
        except:
            pass
        await message.answer("Пользователь забанен нахуй!")


@dp.message_handler(regexp='^/profile \d+')
async def profile_handler(message: types.Message):
    user = await sql.get_user(message.chat.id)
    rank = await sql.get_rank(user.rank_id)

    if rank.admin:
        args = message.text.split()[1:]
        selected_user = await sql.get_user(args[0], False)
        if selected_user:
            selected_user = selected_user[0]
            user_rank = await sql.get_rank(selected_user.rank_id)
            await message.answer(
                "⠀   <b>Профиль пользователя:</b>\n\n"
                f"🆔: <code>{selected_user.chatid}</code>\n"
                f"<i>Ранг</i>: <code>{user_rank.name}</code>\n"
                f"<i>Максимум минут</i>: <code>{user_rank.count_min}</code>\n"
                f"<i>Потоков</i>: <code>{await sql.count_threads(message.chat.id)}</code>"
                f"/"
                f"<code>{user_rank.count_threads}</code>\n\n"
                f"<b>Подписка до</b>: "
                f"{subscribe_until(selected_user.rank_until)}"
            )
        else:
            await message.answer("Пользователя не существует.")


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

            if promo[0].rank_until and promo[0].rank_until < time.time():
                await message.answer("Увы, но промокод уже истек :(")
                return

            temp_rank = await sql.get_rank(promo[0].rank_id, False)
            if temp_rank:
                rank = temp_rank[0]
                await sql.change_rank(message.chat.id, promo[0].rank_id, promo[0].rank_until)
                await message.answer(f"<i>По промокоду твой ранг был сменен на</i> {rank.name}\n\n"
                                     f"<b>Подписка до</b>: {subscribe_until(promo[0].rank_until)}")
            else:
                await message.answer("Извини, но такого ранга не существует, со временем все меняется.")
                return
        else:
            await message.answer("Извини, но такого промокода не существует или он уже активирован.")
            return

    if user.rank_until:  # if time expiration set
        if user.rank_until < time.time():  # if expire
            await sql.change_rank(message.chat.id, cfg.DEFOULT_RANK, 0)  # set default rank
            await message.answer(f'Ваш тариф закончился {stamp_to_date(user.rank_until)}')
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
                       f"Приобрести - /buy_{_rank.rank_id}"
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
                    comment = gen_coment("tg_nano", message.chat.id, selected_rank.rank_id, selected_rank.price)
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
                f"<b>Подписка до</b>: {subscribe_until(user.rank_until)}"
            )
        elif rank.admin and message.text == 'Admin panel':
            await message.answer(
                "<b>Statistics</b> — <i>/stats</i>\n"
                "Example: <code>/stats</code>\n"
                "\n"
                "<b>Change user rank</b> — <i>/set_rank chat-id rank-id</i>\n"
                "Example: <code>/set_rank 735801023 0</code>\n"
                "\n"
                "<b>Set expire time</b> — <i>/set_expire chat-id until-time-stamp</i>\n"
                "Example: <code>/set_expire 735801023 1627069275</code>\n"
                "\n"
                "<b>Stop all threads</b> — <i>/stop_threads</i>\n"
                "Example: <code>/stop_threads</code>\n"
                "\n"
                "<b>Gen promo-code</b> — <i>/gen_promo rank-id until-time-stamp</i>\n"
                "Example: <code>/gen_promo 1 1627069275</code>\n"
                "\n"
                "<b>Ban user</b> — <i>/ban chat-id</i>\n"
                "Example: <code>/ban 735801023</code>\n"
                "\n"
                "<b>Get user profile</b> — <i>/profile chat-id</i>\n"
                "Example: <code>/profile 735801023</code>\n"
                # "\n"
                # "<b></b> — <i>/</i>\n"
                # "Example: <code>/</code>\n"
                # "\n"
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
                markup.add("Admin panel")
            else:
                markup.add("🛠Support🛠")

            await message.answer(
                'Приветствую✋\nМеню ниже.',
                reply_markup=markup
            )


@dp.callback_query_handler()
async def inline_callback(query: types.CallbackQuery):
    user = await sql.get_user(query.message.chat.id)
    rank = await sql.get_rank(user.rank_id)

    if not rank.access:
        return

    data_form = query.data.split("::")

    if data_form[0] == 'stop_thr':
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
    else:
        await query.answer()


if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    loop.run_until_complete(sql.delete_threads())
    executor.start_polling(dp, loop=loop, skip_updates=True, relax=0.05)
