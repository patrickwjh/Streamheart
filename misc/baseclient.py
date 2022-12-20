# -*- coding: utf-8 -*-

import ssl
import asyncio
import logging
import websockets
from misc import exceptions, message as msg
from misc.backoff import ExponentialBackoff
from misc.message_manager import MessageManager

logger = logging.getLogger(__name__)


class Client:
    MAX_RECONNECT_TRIES = 480

    def __init__(self, name, wsserver_address, registration=None, subscriptions=None, ssl_cert=None):
        self.name = name
        self.websocket = None
        self.wsserver_address = wsserver_address
        self.backoff = ExponentialBackoff()
        self.reconnect_counter = 0
        self.events = {}
        self.add_event('error', lambda message: logger.debug(f"{str(message)}"))
        self.requests = {}
        self.message_manager = MessageManager()
        self.registration = registration
        self.subscriptions = subscriptions if subscriptions else []
        self.ready = asyncio.Event()
        self.ssl_cert = ssl_cert

        if ssl_cert:
            self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            self.ssl_context.minimum_version = ssl.TLSVersion.TLSv1_3
            self.ssl_context.load_verify_locations(self.ssl_cert)
            self.ssl_context.verify_mode = ssl.CERT_NONE

    async def connect(self):
        if self.ssl_cert:
            reconnect = await self._ssl_connect()
        else:
            reconnect = await self._connect()

        logger.debug(f"{self.name} connection closed")
        self.ready.clear()
        if reconnect is True:
            await self.reconnect()

    async def _ssl_connect(self):
        try:
            async with websockets.connect(f'wss://{self.wsserver_address[0]}:{self.wsserver_address[1]}',
                                          ssl=self.ssl_context) as self.websocket:
                await self._handle()
        except ConnectionRefusedError as error:
            logger.debug(f"{error.strerror}")
        except asyncio.CancelledError:
            if self.websocket.open:
                logger.debug(f"{self.name} connection closed from {self.wsserver_address}")
            await self.websocket.close()
            return False

        return True

    async def _connect(self):
        try:
            async with websockets.connect(
                    f'ws://{self.wsserver_address[0]}:{self.wsserver_address[1]}') as self.websocket:
                await self._handle()
        except ConnectionRefusedError as error:
            logger.debug(f"{error.strerror}")
        except asyncio.CancelledError:
            if self.websocket.open:
                logger.debug(f"{self.name} connection closed from {self.wsserver_address}")
            await self.websocket.close()
            return False

        return True

    async def _handle(self):
        logger.debug(f"{self.name} connected to {self.websocket.remote_address}")
        self.reconnect_counter = 0
        self.backoff.reset()
        consumer_task = asyncio.create_task(self.consumer())
        initial_task = asyncio.create_task(self._initial())

        try:
            done, pending = await asyncio.wait([consumer_task, initial_task],
                                               return_when=asyncio.FIRST_COMPLETED)

            [future.cancel() for future in pending]
            future_exceptions = [future.exception() for future in done if future.exception()]

            if future_exceptions:
                raise future_exceptions[0]
        except exceptions.RegisterException as error:
            logger.error(error)
            return False
        except exceptions.SubscribeException as error:
            logger.error(error)
            return False

        self.ready.set()
        consumer_task = asyncio.create_task(self.consumer())
        await consumer_task

    async def _initial(self):
        if self.registration:
            try:
                await self.send_wait(msg.Request(
                    'Heart', 'Register', self.message_manager.new_id(), name=self.registration))
            except exceptions.RequestTimeout:
                raise exceptions.RegisterException(f"Can't register {self.registration}. No response from Heart")
            except exceptions.ResponseStatusError as error:
                raise exceptions.RegisterException(f"Can't register {self.registration}. error: {error}")

        await self.subscribe(*self.subscriptions)

    async def consumer(self):
        try:
            async for message in self.websocket:
                checked_msg = msg.check_message(message)
                logger.debug(f"Message received: {message}")

                if type(checked_msg) is msg.Event:
                    try:
                        asyncio.create_task(self.events[checked_msg.update_type](checked_msg))
                    except KeyError:
                        logger.debug(f"Unknown update-type: {checked_msg.update_type}")
                elif type(checked_msg) is msg.Request:
                    try:
                        asyncio.create_task(self.requests[checked_msg.request_type](checked_msg))
                    except KeyError:
                        logger.debug(f"Unknown request-type: {checked_msg.request_type}")
                        await self.send(msg.Error(f"Invalid request-type: {checked_msg.request_type}", checked_msg.id))
                elif type(checked_msg) is msg.Response:
                    if checked_msg.id or checked_msg.id == 0:
                        self.message_manager.response_received(checked_msg)
                    else:
                        self.events['error'](message)
                else:
                    logger.error(f"{self.name} received invalid message from {self.wsserver_address}")
        except websockets.ConnectionClosed as error:
            logger.debug(
                f"Connection canceled from {self.wsserver_address} "
                f"({error.code}, reason: {error.reason if error.reason else 'unknown'})")

    async def reconnect(self):
        if self.reconnect_counter >= Client.MAX_RECONNECT_TRIES:
            raise exceptions.ReconnectTimeout()

        self.reconnect_counter += 1
        retry = self.backoff.delay()
        logger.debug(f"Reconnecting {self.name}. Try: {self.reconnect_counter}. Delay: {retry}s")
        sleep_task = asyncio.create_task(self._sleep(retry))
        await sleep_task
        await self.connect()

    async def _sleep(self, delay):
        await asyncio.sleep(delay)

    async def subscribe(self, *args, loop=True):
        backoff = ExponentialBackoff()
        subscribe_try = 0
        done = []

        while True:
            if subscribe_try >= self.MAX_RECONNECT_TRIES:
                raise exceptions.SubscribeException(f"Can't subscribe {args}. Max. tries reached")

            try:
                for sub in args:
                    if sub not in done:
                        await self.send_wait(msg.Request(
                            'Heart', 'Subscribe', self.message_manager.new_id(), name=sub))
                        done.append(sub)
                break
            except exceptions.RequestTimeout as error:
                logger.debug(f"Subscribe. Request timeout with message-id: {error.message_id}")

                if not loop:
                    raise exceptions.SubscribeException(f"Can't subscribe {args}")

                subscribe_try += 1
                await asyncio.sleep(backoff.delay())
                continue
            except exceptions.ResponseStatusError as error:
                logger.debug(f"Subscribe. message-id: {error.message_id}, error: {error}")

                if not loop:
                    raise exceptions.SubscribeException(f"Can't subscribe {args}")

                subscribe_try += 1
                await asyncio.sleep(backoff.delay())
                continue

    async def send(self, message):
        try:
            logger.debug(f"Message send: {message}")
            await self.websocket.send(str(message))
        except websockets.ConnectionClosedOK:
            logger.debug("Can't send. Connection is closed")

    async def send_wait(self, message):
        try:
            logger.debug(f"Message send: {message}")
            await self.websocket.send(str(message))
            request_future = self.message_manager.add_request(message)
            await request_future

            if request_future.result().status is msg.Status.ERROR:
                raise exceptions.ResponseStatusError(request_future.result().error, request_future.result().id)

            return request_future.result()
        except websockets.ConnectionClosedOK:
            logger.debug("Can't send. Connection is closed")

    def add_event(self, name, callback):
        self.events[name] = callback

    def add_request(self, name, callback):
        self.requests[name] = callback

    def __repr__(self):
        return f"Client(name: {self.name}, " \
               f"websocket_address: {self.websocket.local_address if self.websocket else 'None'}, " \
               f"wsserver_address: {self.wsserver_address})"
