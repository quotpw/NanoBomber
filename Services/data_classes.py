from dataclasses import dataclass
from typing import Union


@dataclass
class Service:
    method: str
    url: str
    params: Union[None, dict]
    headers: Union[None, dict]
    data: Union[None, str, dict]
    json: Union[None, dict]
