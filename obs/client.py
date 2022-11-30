# -*- coding: utf-8 -*-

import json
import signal
import asyncio
import logging
import websockets
from misc import exceptions, baseclient, message as msg

APPLICATION_NAME = 'OBS Studio'
DEFAULTHOST = 'localhost'
DEFAULTPORT_MIDDLEWARE = 4445
DEFAULTPORT_OBS = 4444

logger = logging.getLogger(__name__)
middleware_host = DEFAULTHOST
middleware_port = DEFAULTPORT_MIDDLEWARE
obs_host = DEFAULTHOST
obs_port = DEFAULTPORT_OBS


class OBSClient(baseclient.Client):
    def __init__(self, name, wsserver_address, obsserver_address, registration=None, subscriptions=None, ssl_cert=None):
        super().__init__(name, wsserver_address, registration, subscriptions, ssl_cert)
        self.obsserver_address = obsserver_address
        self.websocket_obs = None

    async def _ssl_connect(self):
        try:
            async with websockets.connect(
                    f'ws://{self.obsserver_address[0]}:{self.obsserver_address[1]}') as self.websocket_obs:
                logger.debug(f"{self.name} connected to {self.websocket_obs.remote_address}")
                async with websockets.connect(
                        f'wss://{self.wsserver_address[0]}:{self.wsserver_address[1]}',
                        ssl=self.ssl_context) as self.websocket:
                    await self._handle()
        except ConnectionRefusedError as error:
            logger.debug(f"{error.strerror}")
        except asyncio.CancelledError:
            await self._close()
            return False

        return True

    async def _connect(self):
        try:
            async with websockets.connect(
                    f'ws://{self.obsserver_address[0]}:{self.obsserver_address[1]}') as self.websocket_obs:
                logger.debug(f"{self.name} connected to {self.websocket_obs.remote_address}")
                async with websockets.connect(
                        f'ws://{self.wsserver_address[0]}:{self.wsserver_address[1]}') as self.websocket:
                    await self._handle()
        except ConnectionRefusedError as error:
            logger.debug(f"{error.strerror}")
        except asyncio.CancelledError:
            await self._close()
            return False

        return True

    async def _handle(self):
        logger.debug(f"{self.name} connected to {self.websocket.remote_address}")
        self.reconnect_counter = 0
        self.backoff.reset()
        consumer_task = asyncio.create_task(self.consumer())
        initial_task = asyncio.create_task(self._initial())
        obs_task = asyncio.create_task(self.consumer_obs(True))

        try:
            done, pending = await asyncio.wait([consumer_task, initial_task, obs_task],
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

        obs_task = asyncio.create_task(self.consumer_obs())
        middleware_task = asyncio.create_task(self.consumer_middleware())
        done, pending = await asyncio.wait([obs_task, middleware_task],
                                           return_when=asyncio.FIRST_COMPLETED)

        [future.cancel() for future in pending]
        [future.exception() for future in done if future.exception()]

    async def _close(self):
        if self.websocket_obs.open:
            logger.debug(f"{self.name} connection closed from {self.obsserver_address}")
        await self.websocket_obs.close()
        if self.websocket.open:
            logger.debug(f"{self.name} connection closed from {self.wsserver_address}")
        await self.websocket.close()

    async def consumer_middleware(self):
        try:
            async for message in self.websocket:
                logger.debug(f"From heart: {message}")
                try:
                    request = msg.Request(message=message)

                    if type(request) is msg.Request:
                        json_msg = json.dumps(
                            {**{msg.REQUEST_FIELDS[1]: request.request_type, msg.REQUEST_FIELDS[2]: str(request.id)},
                             **request.additionals})
                        await self.websocket_obs.send(json_msg)
                except exceptions.InvalidRequestError as error:
                    logger.debug(f"{error}, message-id: {error.message_id}")
                except websockets.ConnectionClosedOK:
                    logger.debug(f"heart sent message to closed obs connection")
        except websockets.ConnectionClosed as error:
            logger.debug(
                f"Connection canceled from {self.wsserver_address} "
                f"({error.code}, reason: {error.reason if error.reason else 'unknown'})")

    async def consumer_obs(self, only_connection_check=False):
        try:
            async for message in self.websocket_obs:
                if only_connection_check:
                    continue

                logger.debug(f"From obs: {message}")

                try:
                    await self.send(message)
                except websockets.ConnectionClosedOK:
                    logger.debug("obs sent message to closed heart connection")
        except websockets.ConnectionClosed as error:
            logger.debug(
                f"Connection canceled from {self.obsserver_address} "
                f"({error.code}, reason: {error.reason if error.reason else 'unknown'})")


async def start(host_mw=DEFAULTHOST, port_mw=DEFAULTPORT_MIDDLEWARE, host_obs=DEFAULTHOST, port_obs=DEFAULTPORT_OBS,
                ssl_cert=None):
    global middleware_host, middleware_port, obs_host, obs_port

    middleware_host, middleware_port = host_mw if host_mw else DEFAULTHOST, port_mw if port_mw else \
        DEFAULTPORT_MIDDLEWARE
    obs_host, obs_port = host_obs if host_obs else DEFAULTHOST, port_obs if port_obs else DEFAULTPORT_OBS

    registration = APPLICATION_NAME
    obsclient = OBSClient('obsclient', (middleware_host, middleware_port),
                          (obs_host, obs_port), registration, ssl_cert=ssl_cert)

    task = asyncio.create_task(obsclient.connect())
    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGTERM, stop, task)
    loop.add_signal_handler(signal.SIGINT, stop, task)

    try:
        await task
    except asyncio.CancelledError:
        logger.debug(f"{obsclient.name} stopped")
    except exceptions.ReconnectTimeout:
        logger.error(f"{obsclient.name} reached maximum reconnects")


def stop(task):
    task.cancel()
