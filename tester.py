import asyncio
from misc.message_manager import MessageManager
import logging
from misc import exceptions, message as msg
import subprocess
import os

logging.basicConfig(level=logging.DEBUG)


async def test_task():
    while True:
        print("läuft")
        await asyncio.sleep(1)


async def start():
    m = MessageManager()
    message = msg.Request("as", "asd", 1)
    m.add_request(message)

    t = asyncio.create_task(test_task())

    input("irgendwas: ")

    while True:
        print("while")
        await asyncio.sleep(1)


async def start2():
    fut = asyncio.get_event_loop().create_future()
    # fut.set_result("RESULT")
    fut.set_exception(exceptions.RequestTimeout)

    try:
        await fut
        e = fut.exception()
        print(e)
        # status = fut.result().status
        print("status")
    except exceptions.RequestTimeout:
        print("Request timeout")


# asyncio.run(start2())

# subprocess.Popen('./start_middleware.py')
# os.system('obs')
