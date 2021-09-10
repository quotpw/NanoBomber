import re
import sys
import time

sys.path.append("../..")
import sql


class Sql(sql.Sql):
    async def create_user(self, chat_id, return_user=False, bot=None, message=None):
        ref = None
        if message is not None:
            tmp_ref = re.findall("^/start ref(\d+)", message.text)
            if tmp_ref:
                if await self.get_user(tmp_ref[0], return_user=False):
                    ref = tmp_ref[0]

        await self.async_query(
            f"INSERT INTO `users`(`chatid`, `refer`) VALUES(?, ?)",
            [chat_id, ref],
            _return=0
        )

        if ref is not None and bot is not None:
            # noinspection PyTypeChecker
            await bot.send_message(int(ref), "<b>У вас новый реферал!</b>\n\n"
                                             f"<i>Chatid</i>: <code>{chat_id}</code>\n"
                                             f"<i>Name</i>: <code>{message.chat.full_name}</code>\n"
                                             f"<i>Username</i>: @{message.chat.username}")

        if return_user:
            return await self.get_user(chat_id)

    async def get_users_chatid(self):
        return [chatid[0] for chatid in await self.async_query("SELECT `chatid` FROM `users`", row_type=None)]

    async def get_user(self, chat_id, return_user=True, bot=None, message=None):
        user = await self.async_query(
            'SELECT * FROM `users` WHERE `chatid` = ?',
            [chat_id]
        )
        if user and return_user:
            return user[0]
        elif not return_user:
            return user
        else:
            return await self.create_user(chat_id, return_user=True, bot=bot, message=message)

    async def get_rank(self, rank_id, return_rank=True):
        rank = await self.async_query(
            "SELECT * FROM `ranks` WHERE `id` = ?",
            [rank_id]
        )
        if return_rank:
            return rank[0]
        else:
            return rank

    async def change_rank(self, chat_id, rank_id, until=None):
        # noinspection SqlWithoutWhere
        await self.async_query(
            f"UPDATE `users` SET `rank_id` = ?{'' if until is None else ', `until` = ?'} WHERE `chatid` = ?",
            [rank_id, chat_id] if until is None else [rank_id, until, chat_id],
            _return=0
        )

    async def change_expire(self, chat_id, until):
        await self.async_query(
            "UPDATE `users` SET `until` = ? WHERE `chatid` = ?",
            [int(until), chat_id],
            _return=0
        )

    async def count_of_refers(self, chat_id):
        return (await self.async_query(
            "SELECT COUNT(`chatid`) FROM `users` WHERE `refer` = ?",
            [chat_id]
        ))[0].COUNTchatid

    async def balance_set(self, chat_id, balance):
        await self.async_query(
            f"UPDATE `users` SET `balance` = ? WHERE `chatid` = ?",
            [balance, chat_id],
            _return=0
        )

    async def balance_plus(self, chat_id, plus: int):
        await self.async_query(
            f"UPDATE `users` SET `balance` = `balance` + ? WHERE `chatid` = ?",
            [plus, chat_id],
            _return=0
        )

    async def get_ranks_for_sale(self, except_id=None):
        return await self.async_query(
            'SELECT * FROM `ranks` WHERE `for_sale` = 1 AND `id` != ?',
            [except_id]
        )

    async def count_of_services(self):
        return (await self.async_query(
            "SELECT COUNT(`url`) FROM `services`"
        ))[0].COUNTurl

    async def count_of_users(self):
        return (await self.async_query(
            "SELECT COUNT(`chatid`) FROM `users`"
        ))[0].COUNTchatid

    async def get_ranks(self, row_type="dict"):
        return await self.async_query(
            "SELECT `id`, `name` FROM `ranks` ORDER BY `id`",
            row_type=row_type
        )

    async def get_rank_stats(self):
        ranks = await self.get_ranks(row_type=self.dict_factory)
        i = 0
        for rank in ranks:
            count = (await self.async_query(
                "SELECT COUNT(`chatid`) FROM `users` WHERE `rank_id` = ?",
                [rank['id']]
            ))[0].COUNTchatid
            ranks[i].update({'count': count})
            i += 1
        return ranks

    async def get_admins(self):
        return await self.async_query(
            'SELECT `chatid` FROM `users` WHERE `rank_id` = 10'
        )

    async def count_threads(self, chat_id=None):
        return (await self.async_query(
            f"SELECT COUNT(`uuid`) FROM `threads` WHERE `until` > ? {'' if chat_id is None else ' AND `chatid` = ?'}",
            [int(time.time())] if chat_id is None else [int(time.time()), chat_id]
        ))[0].COUNTuuid

    async def thread_alive(self, thread_id):
        return bool((await self.async_query(
            f"SELECT COUNT(`uuid`) FROM `threads` WHERE `uuid` = ?",
            [thread_id]
        ))[0].COUNTuuid)

    async def delete_threads(self):
        # noinspection SqlWithoutWhere
        await self.async_query(
            "DELETE FROM `threads`",
            _return=0
        )

    async def delete_thread(self, uuid, chat_id):
        await self.async_query(
            "DELETE FROM `threads` WHERE `uuid` = ? AND `chatid` = ?",
            [uuid, chat_id],
            _return=0
        )

    async def delete_user_threads(self, chat_id):
        await self.async_query(
            "DELETE FROM `threads` WHERE `chatid` = ?",
            [chat_id],
            _return=0
        )

    async def create_thread(self, uuid, chat_id, until):
        await self.async_query(
            "INSERT INTO `threads` VALUES(?, ?, ?)",
            [chat_id, uuid, until],
            _return=0
        )

    async def count_promo(self):
        return (await self.async_query(
            f"SELECT COUNT(`uuid`) FROM `promo`"
        ))[0].COUNTuuid

    async def delete_all_promo(self):
        # noinspection SqlWithoutWhere
        await self.async_query(
            "DELETE FROM `promo`",
            _return=0
        )

    async def create_promo(self, uuid, rank_id, until):
        await self.async_query(
            "INSERT INTO `promo` VALUES(?, ?, ?)",
            [uuid, rank_id, until],
            _return=0
        )
        return uuid

    async def get_promo(self, uuid):
        return await self.async_query(
            "SELECT * FROM `promo` WHERE `uuid` = ?",
            [uuid]
        )

    async def delete_promo(self, uuid):
        await self.async_query(
            "DELETE FROM `promo` WHERE `uuid` = ?",
            [uuid],
            _return=0
        )
