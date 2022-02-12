import os
TG_TOKEN = os.getenv('TG_TOKEN') if os.getenv('TG_TOKEN') else "telegram token"
host = os.getenv('MYSQL_HOST') if os.getenv('MYSQL_HOST') else "mysql host"
user = os.getenv('MYSQL_USER') if os.getenv('MYSQL_USER') else "mysql username"
passwd = os.getenv('MYSQL_PASS') if os.getenv('MYSQL_PASS') else "mysql password"
db = os.getenv('MYSQL_DB') if os.getenv('MYSQL_DB') else "mysql database name"

DB_CONF = {"host": host, "user": user, "password": passwd, "db": db}
DEFAULT_RANK = 0
REF_PROC = 15
