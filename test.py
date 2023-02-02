import asyncio
import logging

from constants import LOG_LEVEL, LOG_FILE_PATH

async def task1():
    while True:
        print("Hello World from Task 1")
        await asyncio.sleep(1)

async def task2():
    while True:
        print("Hello World from Task 2")
        await asyncio.sleep(1)

async def main():
    # Configure logging
    logging.basicConfig(
        level=LOG_LEVEL,
        filename=LOG_FILE_PATH,
        format='[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%m-%d %H:%M:%S')
    await asyncio.gather(task1(), task2())

if __name__ == "__main__":
    asyncio.run(main())