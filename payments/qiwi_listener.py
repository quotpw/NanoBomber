import sys

import glQiwiApi.types

sys.path.append("..")

import re
import sys
import time

from sql import Sql
from engines.telegram.config_file import DB_CONF, TG_TOKEN
import asyncio
import os
from hashlib import md5

if os.name == 'nt':  # If os == Шindows
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())  # fix for "Asyncio Event Loop is Closed"
from glQiwiApi import QiwiWrapper, types
from aiogram import Bot, types as _types
import sentry_sdk

os.chdir(os.path.dirname(os.path.realpath(__file__)))

sentry_sdk.init("https://bc718a3b56bc431c900a306875f54628@o453662.ingest.sentry.io/5944931", traces_sample_rate=1.0)
bot = Bot(token='1809099424:AAF9oqmz3IEXpdUmCFArpoiFWiJXJY0PF7w', parse_mode=_types.ParseMode.HTML)
sql = Sql(**DB_CONF)
qiwi_token = '6b58503ce511fd5b00146acbd29c60cd'
qiwi_phone = '79384302457'
listen_delay = 3
until = 31536000


async def tg_nano(chat_id, rank_id):
    await sql.async_query(
        "UPDATE `users` SET `rank_id` = ?, `until` = ? WHERE `chatid` = ?",
        [rank_id, int(time.time()) + until, chat_id]
    )
    try:
        return
        await Bot(TG_TOKEN).send_message(
            int(chat_id),
            "Оплата прошла успешно, нажмите /start"
        )
    except:
        pass


projects = {
    'tg_nano': tg_nano
}


def gen_hashsum(project_name, chat_id, rank_id, amount):
    return md5(f'{project_name}{chat_id}{rank_id}-{amount}'[::-1].encode()).hexdigest()[-5:]


async def new_payment(transaction: types.Transaction):
    trans_text=f"<i>Сумма</i>: <code>{transaction.sum.amount}</code>{transaction.sum.currency.symbol}\n" \
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
                    # await func(args[1], args[2])
                    await bot.send_message(1546285582, f'<b>Оплата подписки :)</b>\n\n{trans_text}')
                    return
    await bot.send_message(1546285582, f'<b>Неопределенная транзакция.</b>\n\n{trans_text}')


async def main():
    async with QiwiWrapper(api_access_token=qiwi_token, without_context=True) as w:
        w.phone_number = qiwi_phone
        while True:
            # noinspection PyTypeChecker
            transactions = await w.transactions(operation=glQiwiApi.types.TransactionType.IN)
            for trans in transactions:

                print(trans)
                count = (await sql.async_query(
                    "SELECT COUNT(`id`) FROM `qiwi_transactions` WHERE `id` = ?",
                    [int(trans.id)]
                ))[0].COUNTid
                if not count:
                    print("okay")
                    await sql.async_query("INSERT INTO `qiwi_transactions` VALUES(?)", [trans.id])
                    await new_payment(trans)
                else:
                    break

            await asyncio.sleep(listen_delay)


asyncio.run(main())
