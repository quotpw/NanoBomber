import phonenumbers as ph
from phonenumbers import carrier
import random
import re
import uuid


class Phone:
    def __init__(self, phone: str, laungue="en"):
        try:
            obj = ph.parse('+' + phone, keep_raw_input=True)
            self.region = carrier.region_code_for_number(obj).lower()
            self.operator = carrier.name_for_number(obj, laungue)
        except:
            self.valid = False
            return
        self.valid = ph.is_valid_number(obj)

        self.num = str(obj.national_number)
        self.code = str(obj.country_code)
        self.number = self.code + self.num

    def prepare_text(self, text):
        if not text:
            return text
        return self.variables(self.format(text))

    def format(self, text):
        if not text:
            return text
        num = self.number[::-1]
        text = text[::-1]
        for c in list(num):
            text = text.replace("*", c, 1)
        return text[::-1]

    def variables(self, text):
        if not text:
            return text
        # noinspection RegExpRedundantEscape
        matches = re.findall(r"<([\w\d\|]+)>", text)
        if len(matches) > 0:
            for m in matches:
                new = m
                lower = m.lower()
                if lower == 'uuid':
                    new = str(uuid.uuid4())
                elif 'randint' in lower:
                    ran = m.split("|")
                    if len(ran) == 1:
                        new = str(random.randint(100000000, 999999999))
                    else:
                        new = str(random.randint(int(ran[1]), int(ran[2])))
                elif lower == 'phone':
                    new = self.number
                text = text.replace(f"<{m}>", new)
        return text

    def __repr__(self):
        return f"""Phone<(+{self.code}){self.num}|Region: [{self.region}]|Operator: [{self.operator}]>"""
