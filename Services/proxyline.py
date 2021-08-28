import random

import requests
from time import time as stamp

REQ_IN_SEC = 12


class Proxyline:
    def __init__(self, key):
        self.sess = requests.Session()
        self.sess.headers.update({'API-KEY': key})
        self.journal = {}
        self.last_req = 0
        self.last_proxy_index = None

    def request(self, method, params: dict = None):
        if self.last_req + REQ_IN_SEC < stamp():
            try:
                resp = self.sess.get(
                    f'https://panel.proxyline.net/api/{method}/',
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
            method='proxies',
            params={
                'status': 'active'
            }
        )

    # noinspection PyShadowingNames
    @property
    def proxies(self):
        temp = self.getproxy().json()
        proxies = []
        for proxy in temp["results"]:
            proxies.append(f"http://{proxy['username']}:{proxy['password']}@{proxy['ip']}:{proxy['port_http']}")
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


proxy = Proxyline('icxwadd5qxf22bvt2f9cn0n6c1v5rnb5x7nuwq7f')
