import asyncio
import time
import logging

from _thread import start_new_thread
from constants import LOG_LEVEL, LOG_FILE_PATH

async def heartbeat(connection):
    while True:
        logging.info("heartbeat for connection %s", connection)
        await asyncio.sleep(1)

async def send_payload(connection):
    i = 0
    while True:
        i += 1
        logging.info("payload %s for connection %s", i , connection)
        await asyncio.sleep(1)
        if i == 8:
            break

async def run_client_handler(connection):
    await asyncio.gather(heartbeat(connection), send_payload(connection))

def add_new_connection(connection):
    asyncio.run(run_client_handler(connection))

async def main():

    logging.basicConfig(
        level=LOG_LEVEL,
        filename=LOG_FILE_PATH,
        format='[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%m-%d %H:%M:%S'
        )

    connection = 1
    while True:
        start_new_thread(add_new_connection, (connection,))
        connection += 1
        time.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())