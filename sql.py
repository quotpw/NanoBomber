import asyncio
import os
import uuid
from collections import namedtuple
from typing import Iterable, Any
import aiomysql

if os.name == 'nt':  # If os == Шindows
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())  # fix for "Asyncio Event Loop is Closed"


class Struct:
    def __init__(self, **entries):
        self.__dict__.update(entries)


obj_factory = "obj"
dict_factory = "dict"
normal_factory = None


def check_str_in(string: str, vals: list[str]):
    for val in vals:
        if val in string:
            return True
    return False


class Sql:
    def __init__(self, host, user, password, db):
        self.database = {"host": host, "user": user, "password": password, "db": db}

    async def async_query(self, query: str, params: Iterable[Any] = None, _return: int = 1, row_type=obj_factory):
        query = query.replace("?", "%s")

        async with aiomysql.connect(**self.database) as conn:
            await conn.autocommit(True)
            if row_type == normal_factory:
                cur = await conn.cursor()
            else:
                cur = await conn.cursor(aiomysql.DictCursor)
            await cur.execute(query, params)
            if _return:
                if _return == 1:
                    data = await cur.fetchall()
                    if row_type == obj_factory:
                        tmp_data = data
                        data = []
                        for dictionary in tmp_data:
                            for key in list(dictionary):
                                dictionary[key.replace('(', '').replace(')', '').replace('`', '')] = dictionary.pop(key)
                            data.append(namedtuple("fetch", dictionary.keys())(*dictionary.values()))
                    return data
                elif _return == 2:
                    return cur.lastrowid

    def query(self, query: str, params: Iterable[Any] = None, _return: int = 1, row_type=obj_factory):
        return asyncio.run(self.async_query(query, params, _return, row_type))
