# -*- coding: utf-8 -*-

import asyncio
import logging
from misc import exceptions

logger = logging.getLogger(__name__)


class MessageManager:
    MAX_WAIT_TIME = 6

    def __init__(self):
        self.id = 0
        self.request_awaits = {}

    def new_id(self):
        self.id, old_id = self.id + 1, self.id
        return old_id

    def add_request(self, request):
        message_id = request.id
        loop = asyncio.get_event_loop()
        request_future = loop.create_future()
        loop.create_task(self.request_timeout(message_id, request_future))
        self.request_awaits[message_id] = request_future

        return request_future

    async def request_timeout(self, request_id, future):
        try:
            await asyncio.wait_for(asyncio.shield(future), MessageManager.MAX_WAIT_TIME)
        except asyncio.TimeoutError:
            future.set_exception(exceptions.RequestTimeout(request_id))
            logger.debug(f"Awaited request timeout (message-id: {request_id})")
        finally:
            try:
                self.request_awaits.pop(request_id)
            except KeyError:
                logger.debug(f"Timeouted request isn't in request_awaits anymore (message-id: {request_id})")

    def response_received(self, response):
        try:
            request = self.request_awaits[response.id]
            request.set_result(response)
        except KeyError:
            logger.debug(f"Response discarded. Request isn't in request_awaits. message-id: {response.id}")
