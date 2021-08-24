import asyncio
import os
from collections import namedtuple
from typing import Iterable, Any
import aiosqlite

if os.name == 'nt':  # If os == Шindows
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())  # fix for "Asyncio Event Loop is Closed"


class Struct:
    def __init__(self, **entries):
        self.__dict__.update(entries)


def obj_factory(cursor, _row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0].replace('(', '').replace(')', '')] = _row[idx]
    return namedtuple("Row", d.keys())(*d.values())


def dict_factory(cursor, _row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = _row[idx]
    return d


class Sql:
    def __init__(self, db_name: str):
        self.database = db_name

    async def async_query(self, query: str, params: Iterable[Any] = None, _return: int = 1, row_type=obj_factory):
        async with aiosqlite.connect(self.database, isolation_level=None) as db:
            if _return:
                db.row_factory = row_type
                cursor = await db.execute(query, params)
                if _return == 1:
                    return await cursor.fetchall()
                elif _return == 2:
                    return cursor.lastrowid
            else:
                await db.execute(query, params)

    def query(self, query: str, params: Iterable[Any] = None, _return: int = 1, row_type=obj_factory):
        return asyncio.run(self.async_query(query, params, _return, row_type))
