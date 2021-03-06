import re

import requests
from time import time as stamp
import random

UPDATE_EVERY = 600  # every 10min
MAX_ERRORS = 3


class Proxy:
    def __init__(self, ip_port, proxy_type, report_handler=None, report_args=None):
        if report_args is None:
            report_args = []

        self.report_handler = report_handler
        self.report_args = report_args

        self.errors = 0

        self.ip, self.port = ip_port.split(':')
        self.ip_port = ip_port
        self.proxy_type = proxy_type

    def __str__(self):
        return f"{self.proxy_type}://{self.ip_port}"

    def __repr__(self):
        return f'Proxy("{self.ip_port}", "{self.proxy_type}")'


class Proxoid:
    def __init__(self, key, default_type="socks4"):
        self.default_type = default_type
        self.key = key
        self.journal = {}
        self.last_req = 0
        self.last_proxy_index = None

    def request(self, types='all', countries='all', level='all', speed=1500, count=0):
        journal_str = types

        if self.last_req + UPDATE_EVERY < stamp():
            self.last_req = stamp()
            try:
                resp = requests.get(
                    f'https://proxoid.net/api/getProxy',
                    params={
                        'key': self.key,
                        'types': types,
                        "countries": countries,
                        "level": level,
                        "speed": speed,
                        "count": count
                    }
                ).text

                proxies = []
                for p in re.findall('\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d*', resp):
                    obj = Proxy(p, types)
                    proxies.append(obj)

                self.journal[journal_str] = proxies
                return proxies
            except:
                self.last_req = 0

        return self.journal.get(journal_str)

    @property
    def proxies(self):
        proxies = self.request(self.default_type)
        if not proxies:
            self.last_req = 0
            return self.request(self.default_type)
        else:
            return proxies

    @property
    def random_proxy(self):
        return random.choice(self.proxies)

    @property
    def rotated_proxy(self):
        proxies = self.proxies

        if self.last_proxy_index is None:
            pass
        elif self.last_proxy_index + 1 < len(proxies):
            self.last_proxy_index += 1
            return proxies[self.last_proxy_index]

        self.last_proxy_index = 0
        return proxies[0]
