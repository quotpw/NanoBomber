import asyncio

import aiohttp
import aiohttp_socks as aioproxy
import os
import logging
import orjson

from Services.data_classes import Service

if os.name == 'nt':  # If os == Шindows
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())  # fix for "Asyncio Event Loop is Closed"


class Requester:
    def __init__(
            self, services: list[Service] = None,
            timeout: int = 15,
            proxy=None
    ):
        self.timeout = timeout
        self.default_headers = {
            'Connection': 'close',
        }
        self.services = services
        self.proxy = proxy
        self.debug = False

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def __exception_handler(self, loop, context):
        pass

    def set_http_requests(self, services: list[Service]):
        self.services = services

    async def __request(self, session: aiohttp.ClientSession, semaphore, service: Service):
        try:
            async with semaphore, session.request(
                    method=service.method,
                    url=service.url,
                    params=service.params,
                    headers={**self.default_headers, **({} if service.headers is None else service.headers)},
                    data=service.data,
                    json=service.json,
                    ssl=None,
                    verify_ssl=False
            ) as req:
                if self.debug:
                    print(req.real_url)
                    print(f'Status-code: {req.status}\n')
                    text = await req.text()
                    try:
                        print("json:", orjson.loads(text))
                    except:
                        print("text:", text)
                    print("============================\n\n\n")
        except Exception as err:
            logging.info(service.url + "\n" + str(err))

    async def async_run(self, size=50):
        loop = asyncio.get_event_loop()
        loop.set_exception_handler(self.__exception_handler)

        semaphore = asyncio.Semaphore(size)

        # init proxy-connector if proxy set.
        connector = None
        if self.proxy:
            connector = aioproxy.ProxyConnector.from_url(str(self.proxy))

        async with aiohttp.ClientSession(connector=connector,
                                         timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
            await asyncio.gather(
                *[asyncio.ensure_future(
                    self.__request(session, semaphore, service)
                ) for service in self.services]
            )

    def run(self, size=50):
        asyncio.run(self.async_run(size))
