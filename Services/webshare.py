import random
from time import time as stamp

import requests

REQ_IN_SEC = 60


class Webshare:
    def __init__(self, key):
        self.sess = requests.Session()
        self.sess.headers.update({'Authorization': f"Token {key}"})
        self.journal = {}
        self.last_req = 0
        self.last_proxy_index = None

    def request(self, method, params: dict = None):
        if self.last_req + REQ_IN_SEC < stamp():
            try:
                resp = self.sess.get(
                    f'https://proxy.webshare.io/api/{method}',
                    params=params
                )
                self.last_req = stamp()
                self.journal[method] = resp
                return resp
            except:
                pass
        return self.journal.get(method)

    def getproxy(self):
        return self.request(
            method='proxy/list/'
        )

    @property
    def proxies(self):
        temp = self.getproxy().json()
        proxies = []
        for _proxy in temp["results"]:
            proxies.append(
                f"socks5://{_proxy['username']}:{_proxy['password']}@{_proxy['proxy_address']}:{_proxy['ports']['socks5']}"
            )
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


proxy = Webshare('f2b2452b4adf4c8c528476887cf81097a0f07206')
