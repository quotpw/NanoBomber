import asyncio
import os
import random

import orjson

import sql
from Services.requester import Requester
from Services.phone import Phone
from sql import Sql
from Services.data_classes import Service

if os.name == 'nt':  # If os == Шindows
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())  # fix for "Asyncio Event Loop is Closed"


class Services:
    # noinspection PyShadowingNames
    def __init__(self, phone: Phone, services: list[Service] = None):
        if not phone.valid:
            raise Exception("Phone is not valid [class Services]")

        if services is None:
            services = []
        self.phone = phone
        self.services = [*services]

    # noinspection SqlResolve
    async def async_load_from_sqlite3(self, db_conf, db_table, region_column='region'):
        self.services.clear()
        db = Sql(**db_conf)
        rows = await db.async_query(
            f"SELECT * FROM `{db_table}` WHERE `{region_column}` IS NULL OR `{region_column}` = ?",
            [self.phone.region],
            row_type=sql.dict_factory
        )
        for row_service in rows:
            self.services.append(Service(
                row_service.get('method'),
                row_service.get('url'),
                row_service.get('params'),
                row_service.get('headers'),
                row_service.get('data'),
                row_service.get('json')
            ))

    def load_from_sqlite3(self, db_name, db_table, region_column='region'):
        asyncio.run(self.async_load_from_sqlite3(db_name, db_table, region_column))

    def prepare_service(self, service: Service):
        url = self.phone.prepare_text(service.url)
        params = None
        headers = None
        data = None
        json = None

        if service.params:
            params = orjson.loads(self.phone.prepare_text(service.params))

        if service.headers:
            headers = orjson.loads(self.phone.prepare_text(service.headers))

        if service.data:
            if service.data[0] == '{' and service.data[-1] == '}':
                data = orjson.loads(self.phone.prepare_text(service.data))
            else:
                data = self.phone.prepare_text(service.data)

        if service.json:
            try:
                json = orjson.loads(self.phone.prepare_text(service.json))
            except:
                print(self.phone.prepare_text(service.json))

        return Service(service.method.lower(), url, params, headers, data, json)

    @property
    def prepared_services(self):
        services_list = [self.prepare_service(service) for service in self.services]
        random.shuffle(services_list)
        return services_list

    async def async_run(self, timeout=12, size=50, proxy=None):
        req = Requester(self.prepared_services, timeout, proxy)
        await req.async_run(size)

    def run(self, timeout=12, size=50, proxy=None, debug=False):
        req = Requester(self.prepared_services, timeout, proxy)
        req.debug = debug
        req.run(size)
