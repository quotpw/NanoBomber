#!/bin/bash

cd payments
exec python3 qiwi_listener.py &
cd ../engines/telegram/web_services/
exec python3 main.py &
cd ../
exec python3 main.py &
