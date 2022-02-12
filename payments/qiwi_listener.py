import logging
import sys
import traceback

import glQiwiApi.types

sys.path.append("..")

import re
import time

from sql import Sql
from engines.telegram.config_file import DB_CONF, TG_TOKEN, REF_PROC
from engines.telegram import _sql
import asyncio
import os
from hashlib import md5

if os.name == 'nt':  # If os == Шindows
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())  # fix for "Asyncio Event Loop is Closed"
from glQiwiApi import QiwiWrapper, types
from aiogram import Bot, types as _types
import sentry_sdk

os.chdir(os.path.dirname(os.path.realpath(__file__)))

bot = Bot(token='payment notifier tg token', parse_mode=_types.ParseMode.HTML)
sql = Sql(**DB_CONF)
nano_sql = _sql.Sql(**DB_CONF)
qiwi_token = 'qiwi token'
qiwi_phone = 'phone token'
listen_delay = 3
until = 31536000

tg_nano_bot = Bot(TG_TOKEN, parse_mode=_types.ParseMode.HTML)
tg_nano_markup = _types.ReplyKeyboardMarkup(resize_keyboard=True)
tg_nano_markup.add("💣BOMB💣")
tg_nano_markup.add("👤Профиль👤")
tg_nano_markup.add("🛠Support🛠")


async def tg_nano(chat_id, rank_id, money: int):
    await nano_sql.change_rank(chat_id, rank_id, int(time.time()) + until)
    try:
        await tg_nano_bot.send_message(
            int(chat_id),
            "Оплата прошла успешно, нажмите /start",
            reply_markup=tg_nano_markup
        )
    except:
        logging.error(traceback.format_exc())

    user = await nano_sql.get_user(chat_id, return_user=False)
    if user:
        user = user[0]
        if user.refer is not None:
            await nano_sql.balance_plus(user.refer, int(money * (REF_PROC / 100)))
            try:
                chat = await tg_nano_bot.get_chat(user.chatid)
                await tg_nano_bot.send_message(
                    user.refer,
                    f"<b>Пользователь приобрел подписку за {money}rub, вам было начислено {int(money * (REF_PROC / 100))}rub.</b>\n\n"
                    f"<i>Chatid</i>: <code>{chat.id}</code>\n"
                    f"<i>Name</i>: <code>{chat.full_name}</code>\n"
                    f"<i>Username</i>: @{chat.username}"
                )
            except:
                logging.error(traceback.format_exc())


projects = {
    'tg_nano': tg_nano
}


def gen_hashsum(project_name, chat_id, rank_id, amount):
    return md5(f'{project_name}{chat_id}{rank_id}-{amount}'[::-1].encode()).hexdigest()[-5:]


async def new_payment(transaction: types.Transaction):
    trans_text = f"<i>Сумма</i>: <code>{transaction.sum.amount}</code>{transaction.sum.currency.symbol}\n" \
                 f"<i>От кого</i>: {transaction.to_account}\n" \
                 f"<i>Дата</i>: {transaction.date.strftime('<code>%x</code> - <code>%X</code>')}\n" \
                 f"{f'<i>Коментарий</i>: <code>{transaction.comment}</code>' if transaction.comment else ''}"
    if transaction.comment:
        args = re.findall('(.*?)::(\d*)::(\d*)::(\d*)::(.{5})', transaction.comment)
        if args:
            args = args[0]
            if gen_hashsum(args[0], args[1], args[2], args[3]) == args[4] and int(transaction.sum.amount) >= int(
                    args[3]):
                func = projects.get(args[0])
                if func:
                    await func(args[1], args[2], int(transaction.sum.amount))
                    await bot.send_message(admin_chat_id, f'<b>Оплата подписки :)</b>\n\n{trans_text}')
                    return
    await bot.send_message(admin_chat_id, f'<b>Неопределенная транзакция.</b>\n\n{trans_text}')


async def main():
    async with QiwiWrapper(api_access_token=qiwi_token, without_context=True) as w:
        w.phone_number = qiwi_phone
        while True:
            # noinspection PyTypeChecker
            transactions = await w.transactions(operation=glQiwiApi.types.TransactionType.IN)
            for trans in transactions:
                count = (await sql.async_query(
                    "SELECT COUNT(`id`) FROM `qiwi_transactions` WHERE `id` = ?",
                    [int(trans.id)]
                ))[0].COUNTid
                if not count:
                    await sql.async_query("INSERT INTO `qiwi_transactions` VALUES(?)", [trans.id])
                    await new_payment(trans)
                else:
                    break

            await asyncio.sleep(listen_delay)


asyncio.run(main())
