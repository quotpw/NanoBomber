import sys

sys.path.append("..")

import re
import sys
import time

sys.path.append("../..")
from sql import Sql
import asyncio
import os
from hashlib import md5

if os.name == 'nt':  # If os == Шindows
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())  # fix for "Asyncio Event Loop is Closed"
from glQiwiApi import QiwiWrapper, types
from aiogram import Bot, types as _types

os.chdir(os.path.dirname(os.path.realpath(__file__)))

bot = Bot(token='1809099424:AAF9oqmz3IEXpdUmCFArpoiFWiJXJY0PF7w', parse_mode=_types.ParseMode.HTML)
sql = Sql('database.db')
qiwi_token = '6b58503ce511fd5b00146acbd29c60cd'
qiwi_phone = '79384302457'
listen_delay = 3
until = 31536000


async def tg_nano(chat_id, rank_id):
    await Sql("../engines/telegram/NanoBomber.db").async_query(
        "UPDATE users SET rank_id = ?, rank_until = ? WHERE chatid = ?",
        [rank_id, int(time.time()) + until, chat_id]
    )
    try:
        await Bot("1117915604:AAEw3UqzzU_GIdfxMif8lJDCwmmQeKfPWx4").send_message(
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
    if transaction.comment:
        args = re.findall('(.*?)::(\d*)::(\d*)::(\d*)::(.{5})', transaction.comment)
        if args:
            args = args[0]
            if gen_hashsum(args[0], args[1], args[2], args[3]) == args[4] and int(transaction.sum.amount) >= int(
                    args[3]):
                func = projects.get(args[0])
                if func:
                    await func(args[1], args[2])
                    await bot.send_message(1546285582, f'Оплата подписки :)\n\n{transaction}')
                    return
    await bot.send_message(1546285582, f'Халява ебать!\n\n{transaction}')


async def main():
    async with QiwiWrapper(api_access_token=qiwi_token, without_context=True) as w:
        w.phone_number = qiwi_phone
        while True:
            try:
                transactions = await w.transactions(operation='IN')
                for trans in transactions:
                    count = (await sql.async_query(
                        "SELECT COUNT(id) FROM transactions WHERE id = ?",
                        [trans.transaction_id]
                    ))[0].COUNTid
                    if not count:
                        await sql.async_query("INSERT INTO transactions VALUES(?)", [trans.transaction_id])
                        await new_payment(trans)
                    else:
                        break
            except Exception as err:
                print(err)

            await asyncio.sleep(listen_delay)


asyncio.run(main())
