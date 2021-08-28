import sys
import time

sys.path.append("../..")
import sql


class Sql(sql.Sql):
    async def create_user(self, chat_id, return_user=False):
        await self.async_query(
            "INSERT INTO users(chatid) VALUES(?)",
            [chat_id],
            _return=0
        )
        if return_user:
            return await self.get_user(chat_id)

    async def get_users_chatid(self):
        return [chatid[0] for chatid in await self.async_query("SELECT chatid FROM users", row_type=None)]

    async def get_user(self, chat_id, return_user=True):
        user = await self.async_query(
            'SELECT * FROM users WHERE chatid = ?',
            [chat_id]
        )
        if user and return_user:
            return user[0]
        elif not return_user:
            return user
        else:
            return await self.create_user(chat_id, return_user=True)

    async def get_rank(self, rank_id, return_rank=True):
        rank = await self.async_query(
            "SELECT * FROM ranks WHERE rank_id = ?",
            [rank_id]
        )
        if return_rank:
            return rank[0]
        else:
            return rank

    async def change_rank(self, chat_id, rank_id, until=None):
        # noinspection SqlWithoutWhere
        await self.async_query(
            f"UPDATE users SET rank_id = ?{'' if until is None else ', rank_until = ?'} WHERE chatid = ?",
            [rank_id, chat_id] if until is None else [rank_id, until, chat_id],
            _return=0
        )

    async def change_expire(self, chat_id, until):
        await self.async_query(
            "UPDATE users SET rank_until = ? WHERE chatid = ?",
            [int(until), chat_id],
            _return=0
        )

    async def get_ranks_for_sale(self, except_id=None):
        return await self.async_query(
            'SELECT * FROM ranks WHERE for_sale = 1 AND rank_id != ?',
            [except_id]
        )

    async def count_of_services(self):
        return (await self.async_query(
            "SELECT COUNT(url) FROM services"
        ))[0].COUNTurl

    async def count_of_users(self):
        return (await self.async_query(
            "SELECT COUNT(chatid) FROM users"
        ))[0].COUNTchatid

    async def get_ranks(self, row_type=sql.obj_factory):
        return await self.async_query(
            "SELECT rank_id, name FROM ranks ORDER BY rank_id",
            row_type=row_type
        )

    async def get_rank_stats(self):
        ranks = await self.get_ranks(row_type=sql.dict_factory)
        i = 0
        for rank in ranks:
            count = (await self.async_query(
                "SELECT COUNT(chatid) FROM users WHERE rank_id = ?",
                [rank['rank_id']]
            ))[0].COUNTchatid
            ranks[i].update({'count': count})
            i += 1
        return ranks

    async def get_admins(self):
        return await self.async_query(
            'SELECT chatid FROM users WHERE rank_id = 10'
        )

    async def count_threads(self, chat_id=None):
        return (await self.async_query(
            f"SELECT COUNT(uuid) FROM threads WHERE until > ? {'' if chat_id is None else ' AND chatid = ?'}",
            [int(time.time())] if chat_id is None else [int(time.time()), chat_id]
        ))[0].COUNTuuid

    async def thread_alive(self, thread_id):
        return bool((await self.async_query(
            f"SELECT COUNT(uuid) FROM threads WHERE uuid = ?",
            [thread_id]
        ))[0].COUNTuuid)

    async def delete_threads(self):
        # noinspection SqlWithoutWhere
        await self.async_query(
            "DELETE FROM threads",
            _return=0
        )

    async def delete_thread(self, uuid, chat_id):
        await self.async_query(
            "DELETE FROM threads WHERE uuid = ? AND chatid = ?",
            [uuid, chat_id],
            _return=0
        )

    async def delete_user_threads(self, chat_id):
        await self.async_query(
            "DELETE FROM threads WHERE chatid = ?",
            [chat_id],
            _return=0
        )

    async def create_thread(self, uuid, chat_id, until):
        await self.async_query(
            "INSERT INTO threads VALUES(?, ?, ?)",
            [uuid, chat_id, until],
            _return=0
        )

    async def count_promo(self):
        return (await self.async_query(
            f"SELECT COUNT(uuid) FROM promo"
        ))[0].COUNTuuid

    async def delete_all_promo(self):
        # noinspection SqlWithoutWhere
        await self.async_query(
            "DELETE FROM promo",
            _return=0
        )

    async def create_promo(self, uuid, rank_id, until):
        await self.async_query(
            "INSERT INTO promo VALUES(?, ?, ?)",
            [uuid, rank_id, until],
            _return=0
        )
        return uuid

    async def get_promo(self, uuid):
        return await self.async_query(
            "SELECT * FROM promo WHERE uuid = ?",
            [uuid]
        )

    async def delete_promo(self, uuid):
        await self.async_query(
            "DELETE FROM promo WHERE uuid = ?",
            [uuid],
            _return=0
        )
