from hashlib import md5
from datetime import datetime


def gen_hashsum(project_name, chat_id, rank_id, amount):
    return md5(f'{project_name}{chat_id}{rank_id}-{amount}'[::-1].encode()).hexdigest()[-5:]


def gen_coment(project_name, chat_id, rank_id, amount):
    return f"{project_name}::{chat_id}::{rank_id}::{amount}::{gen_hashsum(project_name, chat_id, rank_id, amount)}"


def gen_url(to, amount, comment):
    return f"https://qiwi.com/payment/form/99?amountInteger={amount}&" \
           f"amountFraction=0&currency=643&extra['account']={to}&" \
           f"extra['comment']={comment}&blocked[0]=sum&blocked[1]=account&blocked[2]=comment"


def stamp_to_date(stamp, return_time=False):
    if return_time:
        return str(datetime.fromtimestamp(stamp).strftime("%H:%M"))
    else:
        return str(datetime.fromtimestamp(stamp))


def subscribe_until(stamp):
    return 'бесконечности' if not stamp else stamp_to_date(stamp)
