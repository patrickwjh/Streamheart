# -*- coding: utf-8 -*-

import ssl
import signal
import asyncio
import logging
import pathlib
import websockets
from heart import client

logger = logging.getLogger(__name__)
DEFAULTPORT = 4445


class ServerMessageManager:
    # TODO Remove ServerMessageManager. Ideally only one MessageManager class for Server and Clients
    MAX_WAIT_TIME = 6

    def __init__(self):
        self.id = 0
        self.request_awaits = {}

    def new_id(self):
        self.id, old_id = self.id + 1, self.id

        return old_id

    def add_request_await(self, client_websocket, original_messageid, new_messageid):
        loop = asyncio.get_event_loop()
        request_future = loop.create_future()
        loop.create_task(self.request_timeout(new_messageid, request_future))
        self.request_awaits[new_messageid] = (client_websocket, original_messageid, request_future)

    async def request_timeout(self, messageid, future):
        try:
            await asyncio.wait_for(future, ServerMessageManager.MAX_WAIT_TIME)
        except asyncio.TimeoutError:
            logger.debug(f"Awaited request timeout (message-id: {messageid})")
        finally:
            try:
                self.request_awaits.pop(messageid)
            except KeyError:
                logger.debug(f"Timeouted request isn't in request_awaits anymore (message-id: {messageid})")


class Server:
    def __init__(self, host=None, port=DEFAULTPORT, ssl_cert=None):
        self.websocket = None
        self.host = host
        self.port = port
        self.connections = set()
        self.registered_apps = {}
        self.responses = {}
        self.loop = None
        self.stop = None
        self.clientid = 0
        self.message_manager = ServerMessageManager()
        self.ssl_cert = ssl_cert

        if ssl_cert and len(ssl_cert) > 1 and ssl_cert[0] and ssl_cert[1]:
            self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            self.ssl_context.load_cert_chain(self.ssl_cert[0], self.ssl_cert[1])
        else:
            self.ssl_cert = None

    async def start(self):
        self.loop = asyncio.get_event_loop()
        self.stop = self.loop.create_future()

        self.loop.add_signal_handler(signal.SIGTERM, self.stop_server)
        self.loop.add_signal_handler(signal.SIGINT, self.stop_server)

        if self.ssl_cert:
            async with websockets.serve(self._handler, self.host, self.port, ssl=self.ssl_context) as self.websocket:
                logger.debug("Websocket server started")
                await self.stop
                logger.debug("Websocket server stopped")
        else:
            async with websockets.serve(self._handler, self.host, self.port) as self.websocket:
                logger.debug("Websocket server started")
                await self.stop
                logger.debug("Websocket server stopped")

    def stop_server(self):
        self.stop.set_result(None)

    async def _handler(self, websocket: websockets.WebSocketServerProtocol, path):
        context = client.Client(self.new_clientid(), self.message_manager, websocket, self.registered_apps)
        self.register(context)
        consumer_task = asyncio.create_task(self._consumer(context))
        await consumer_task
        await self.unregister(context)

    async def _consumer(self, context):
        try:
            async for wsmessage in context.websocket:
                try:
                    logger.debug(f"Message from ClientID {context.clientid}: {wsmessage}")
                    await context.state.handle(wsmessage)
                except websockets.ConnectionClosedOK:
                    logger.debug(f"{context} sent message to closed connection")
                    pass
        except websockets.ConnectionClosedError as error:
            logger.debug(
                f"Connection closed from {context} "
                f"({error.code}, reason: {error.reason if error.reason else 'unknown'})")

    def register(self, context):
        self.connections.add(context)
        logger.debug(f"{context} connected")

    async def unregister(self, context):
        if context.registration:
            name = context.registration.name
            await context.remove_application(name)

        app_names = list(context.subscriptions.keys())
        [context.remove_subscription(name) for name in app_names]

        self.connections.remove(context)
        logger.debug(f"{context} disconnected")

    def new_clientid(self):
        self.clientid, old_clientid = self.clientid + 1, self.clientid

        return old_clientid
