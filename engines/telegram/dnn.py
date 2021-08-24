import sys
sys.path.append("../..")
import os.path
import sql

dnn_base = sql.Sql('dnn.db')


async def phone_info(phone):
    return await dnn_base.async_query(
        "SELECT * FROM dnn WHERE phone = ?",
        [phone]
    )


async def email_info(email):
    return await dnn_base.async_query(
        "SELECT * FROM dnn WHERE email = ?",
        [email]
    )


async def tg_id_info(tg_id):
    return await dnn_base.async_query(
        "SELECT * FROM dnn WHERE tg_id = ?",
        [tg_id]
    )


def update_result(result, data):
    if data.phone:
        if data.phone not in result['phones']:
            result['phones'].append(data.phone)
    if data.name:
        if data.name not in result['names'] and data.name != ' ':
            result['names'].append(data.name)
    if data.email:
        if data.email not in result['emails']:
            result['emails'].append(data.email)
    if data.tg_id:
        if data.tg_id not in result['tg_ids']:
            result['tg_ids'].append(data.tg_id)
    if data.tg_username:
        if data.tg_username not in result['tg_usernames']:
            result['tg_usernames'].append(data.tg_username)


async def deanon(phone, result=None):
    if not os.path.exists(dnn_base.database):
        return {
            "phones": [f'{dnn_base.database} base not exist :('],
            "names": [],
            "emails": [],
            "tg_ids": [],
            "tg_usernames": []
        }
    if result is None:
        result = {
            "phones": [],
            "names": [],
            "emails": [],
            "tg_ids": [],
            "tg_usernames": []
        }
    for value in await phone_info(phone):
        update_result(result, value)
    for email in result['emails']:
        for value in await email_info(email):
            update_result(result, value)
    for tg_id in result['tg_ids']:
        for value in await tg_id_info(tg_id):
            update_result(result, value)
    return result
