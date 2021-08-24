import random

import requests
from time import time as stamp


class Proxy6:
    def __init__(self, key):
        self.api_key = key
        self.sess = requests.Session()
        self.journal = {}
        self.last_answers = {}
        self.last_proxy_index = None

    def request(self, method, params: dict = None):
        time_stamp = str(int(stamp()))
        count_of_requests = self.journal.get(time_stamp)
        if count_of_requests is not None:
            if count_of_requests == 1:
                return self.last_answers.get(method)
            else:
                self.journal[time_stamp] += 1
        else:
            self.journal = {time_stamp: 1}

        try:
            resp = self.sess.get(
                f'https://proxy6.net/api/{self.api_key}/{method}',
                params=params
            ).json()
        except:
            return self.last_answers.get(method)

        self.last_answers[method] = resp

        return resp

    def getproxy(self):
        return self.request(
            method='getproxy',
            params={
                'state': 'active',
                'nokey': ''
            }
        )

    @property
    def proxies(self):
        temp = self.getproxy()
        proxies = []
        for proxy in temp["list"]:
            proxies.append(f"{proxy['type']}://{proxy['user']}:{proxy['pass']}@{proxy['ip']}:{proxy['port']}")
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


proxy = Proxy6('e2a23e6855-6254629d16-05d51dee77')
