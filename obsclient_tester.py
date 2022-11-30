#!/usr/bin/python3
# -*- coding: utf-8 -*-

import json
import signal
import asyncio
import logging
import websockets

from misc import message

message_id = 0


async def openfifo():
    rx = asyncio.StreamReader()
    fd = open('/usr/local/nginx/nginx-rtmp-module/stream', 'r')
    transport, _ = await asyncio.get_running_loop().connect_read_pipe(lambda: asyncio.StreamReaderProtocol(rx), fd)

    return transport, rx


async def readfifo():
    reader = await openfifo()
    while True:
        line = await reader[1].read()
        print(line.decode('utf-8'))


def stopping(test):
    global stop
    stop = True


async def connect():
    try:
        async with websockets.connect('ws://127.0.0.1:4444') as websocket:
            global message_id, stop
            stop = asyncio.Event()
            asyncio.get_event_loop().add_signal_handler(signal.SIGINT, stop.set)
            asyncio.get_event_loop().add_signal_handler(signal.SIGTERM, stop.set)
            # eingabe = input("Text eingeben: ")

            while not stop.is_set():
                try:
                    # await websocket.send(json.dumps(
                    #     {'application': 'heart', 'request-type': 'Register', 'message-id': message_id,
                    #      'name': 'TestApp'}))
                    # print(f"send message {message_id}")
                    # message_id += 1
                    #
                    # response = await websocket.recv()
                    # print(response)
                    # message.Response(response)
                    #
                    # response = await websocket.recv()
                    # print(response)
                    # message.Response(response)

                    # break
                    # await websocket.send(json.dumps(
                    #     {'application': 'heart', 'request-type': 'Unregister', 'message-id': message_id,
                    #      'name': 'TestApp'}))
                    # print(f"send message {message_id}")
                    # message_id += 1
                    #
                    # response = await websocket.recv()
                    # print(response)
                    # message.Response(response)
                    #
                    # break

                    await websocket.send(json.dumps(
                        {'application': 'heart', 'request-type': 'Subscribe', 'message-id': message_id, 'name': 'Heartrate'}))
                    print(f"send message {message_id}")
                    message_id += 1

                    response = await websocket.recv()
                    print(response)
                    message.Response(message=response)

                    await websocket.send(str(
                        message.Request(application="Heartrate", request_type="EnableBrb", limit=800, message_id=message_id)))

                    response = await websocket.recv()
                    print(response)
                    # message.Response(message=response)

                    # await websocket.send(str(
                    #     message.Request(application="Heartrate", request_type="EnableBrb", message_id=message_id)))
                    #
                    # response = await websocket.recv()
                    # print(response)
                    #
                    # event = await websocket.recv()
                    # print(event)

                    # await websocket.send(str(
                    #     message.Request(application="Heartrate", request_type="EnableBrb", message_id=message_id)))
                    #
                    # response = await websocket.recv()
                    # print(response)
                    #
                    # event = await websocket.recv()
                    # print(event)

                    break

                    # await asyncio.sleep(1)
                    #
                    # await websocket.send(json.dumps(
                    #     {'application': 'TestApp', 'request-type': 'Neu', 'message-id': message_id,
                    #      "name": "eingabe"}))
                    # print(f"send message {message_id}")
                    # message_id += 1
                    #
                    # response = await websocket.recv()
                    # print(response)
                    # message.Response(response)


                    # while True:
                    #     await websocket.recv()
                except websockets.ConnectionClosedOK as ok:
                    if ok.reason == "":
                        logger.info(f"Connection closed ({ok.code})")
                    else:
                        logger.info(f"Connection closed ({ok.code}, {ok.reason})")
                    break
                except websockets.ConnectionClosedError as error:
                    if error.reason == "":
                        logger.info(f"Connection closed ({error.code})")
                    else:
                        logger.info(f"Connection closed ({error.code}, {error.reason})")
                    break

    except ConnectionRefusedError as error:
        logger.error("Connect to server failed")


stop = False

# asyncio.get_event_loop().run_until_complete(readfifo())
logger = logging.getLogger('websockets')
# logger.setLevel(logging.DEBUG)
# logger.addHandler(logging.StreamHandler())
# logging.basicConfig(level=logging.INFO)
asyncio.run(connect())
# print("Finish")
