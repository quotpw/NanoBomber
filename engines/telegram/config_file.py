# Project token: 1117915604:AAHASBIQXVseruTST1nOd3ARy--w4D6yNwg
# Qiwi|Test token: 1809099424:AAF9oqmz3IEXpdUmCFArpoiFWiJXJY0PF7w
import os
TG_TOKEN = os.getenv('TG_TOKEN') if os.getenv('TG_TOKEN') else "1117915604:AAHASBIQXVseruTST1nOd3ARy--w4D6yNwg"
host = os.getenv('MYSQL_HOST') if os.getenv('MYSQL_HOST') else "172.19.0.2"
user = os.getenv('MYSQL_USER') if os.getenv('MYSQL_USER') else "nano"
passwd = os.getenv('MYSQL_PASS') if os.getenv('MYSQL_PASS') else "NanoBomber13372281337!"
db = os.getenv('MYSQL_DB') if os.getenv('MYSQL_DB') else "nanobomber"

DB_CONF = {"host": host, "user": user, "password": passwd, "db": db}
DEFAULT_RANK = 0
REF_PROC = 15
