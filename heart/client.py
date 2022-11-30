# -*- coding: utf-8 -*-

import asyncio
import logging
from heart.events import EVENTS
from heart.request_handler import REQUESTS
from misc import exceptions, message as msg, constants

logger = logging.getLogger(__name__)


class Application:
    def __init__(self, name, websocket=None):
        self.name = name
        self.websocket = websocket
        self.subscribers = set()

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return True if self.name == other else False

    def __repr__(self):
        return f"Application(name: {self.name}, websocket_address: " \
               f"{self.websocket.remote_address}, subscribers: {self.subscribers})"


class Client:
    def __init__(self, clientid, message_manager, websocket, applications):
        self.clientid = clientid
        self.message_manager = message_manager
        self.state = Pending(self)
        self.websocket = websocket
        self.registration = None
        self.subscriptions = {}
        self.all_applications = applications

    async def send(self, message):
        await self.websocket.send(str(message))

    def add_application(self, name):
        if name in self.all_applications:
            raise exceptions.RegisterException(f"{name} is already registered")

        if self.registration:
            raise exceptions.RegisterException(f"Unregister {self.registration.name} first to register {name}")

        application = Application(name, self.websocket)
        self.registration = application
        self.all_applications[application.name] = application
        self.update_state()

    async def remove_application(self, name):
        if self.registration.name != name:
            raise exceptions.UnregisterException(f"You have not {name} registered")

        if self.registration.subscribers:
            done, pending = await asyncio.wait(
                [EVENTS['UnsubscribedFrom'](sub.websocket, name) for sub in self.registration.subscribers])
            [future.cancel() for future in pending]
            [future.exception() for future in done]

        subs = list(self.registration.subscribers)
        [sub.remove_subscription(name) for sub in subs]

        self.registration = None
        self.all_applications.pop(name)
        self.update_state()

    def add_subscription(self, name):
        try:
            app = self.all_applications[name]
        except KeyError:
            raise exceptions.SubscribeException(f"Can't subscribe {name}. It doesn't exist")

        if name in self.subscriptions:
            raise exceptions.SubscribeException(f"{name} is already subscribed")

        app.subscribers.add(self)
        self.subscriptions[name] = app
        self.update_state()

    def remove_subscription(self, name):
        try:
            app = self.subscriptions[name]
        except KeyError:
            raise exceptions.UnsubscribeException(f"{name} is not subscribed")

        app.subscribers.remove(self)
        self.subscriptions.pop(name)
        self.update_state()

    def update_state(self):
        if not self.registration and not len(self.subscriptions):
            self.state = Pending(self)
        elif self.registration and not len(self.subscriptions):
            self.state = Registered(self)
        elif not self.registration and len(self.subscriptions):
            self.state = Subscribed(self)
        else:
            self.state = SubscribedAndRegistered(self)

    def __hash__(self):
        return hash(self.clientid)

    def __eq__(self, other):
        return True if self.clientid == other else False

    def __repr__(self):
        return f"Client(clientID: {self.clientid}, state: {self.state}, websocket_address: " \
               f"{self.websocket.remote_address} registration: {self.registration}, " \
               f"subscriptions: {self.subscriptions.keys()})"


class ClientState:
    def __init__(self, context):
        self.context = context

    def __repr__(self):
        return f"{self.__class__.__name__}(context: {self.context.clientid})"


class Pending(ClientState):
    """
    Pending: Client has no subscriptions and registration
    Handle messages from a client in pending state that are requests to the heart
    """

    async def handle(self, message):
        try:
            request = msg.Request(message=message)

            if request.application == constants.MIDDLEWARE_APPLICATION_NAME:
                await handle_middleware_request(self.context, request)
            else:
                logger.debug(f"Request to {request.application} in pending state")
                await self.context.send(msg.Error("You have no subscriptions", request.id))
        except exceptions.MessageError as error:
            logger.debug(f"Only requests allowed. {str(error)}")
            await self.context.send(msg.Error(f"Only requests allowed. {str(error)}", error.message_id))


class Subscribed(ClientState):
    """
    Subscribed: Client has subscriptions
    Handle messages from a client in subscribed state that are requests
    """

    async def handle(self, message):
        try:
            request = msg.Request(message=message)

            if request.application == constants.MIDDLEWARE_APPLICATION_NAME:
                await handle_middleware_request(self.context, request)
            else:
                await handle_request(self.context, request)
        except exceptions.MessageError as error:
            logger.debug(f"Only requests allowed. {str(error)}")
            await self.context.send(msg.Error(f"Only requests allowed. {str(error)}", error.message_id))


class Registered(ClientState):
    """
    Registered: Client has registration
    Handle messages from a client in registered state that are requests to heart, events or responses
    """

    async def handle(self, message):
        checked_msg = msg.check_message(message)

        if type(checked_msg) is msg.Request:
            if checked_msg.application == constants.MIDDLEWARE_APPLICATION_NAME:
                await handle_middleware_request(self.context, checked_msg)
            else:
                await self.context.websocket.send(str(msg.Error("You have no subscriptions", checked_msg.id)))
        elif type(checked_msg) is msg.Event:
            await handle_event(self.context, checked_msg)
        elif type(checked_msg) is msg.Response:
            await handle_response(self.context, checked_msg)
        else:
            logger.debug(f"Invalid message from {self.context.websocket.remote_address}")
            await self.context.send(msg.Error("Invalid message"))


class SubscribedAndRegistered(ClientState):
    """
    SubscribedAndRegistered: Client has subscriptions and registration
    Handle messages from a client in SubscribedAndRegistered state that are requests, events or responses
    """

    async def handle(self, message):
        checked_msg = msg.check_message(message)

        if type(checked_msg) is msg.Request:
            if checked_msg.application == constants.MIDDLEWARE_APPLICATION_NAME:
                await handle_middleware_request(self.context, checked_msg)
            else:
                await handle_request(self.context, checked_msg)
        elif type(checked_msg) is msg.Event:
            await handle_event(self.context, checked_msg)
        elif type(checked_msg) is msg.Response:
            await handle_response(self.context, checked_msg)
        else:
            logger.debug(f"Invalid message from {self.context.websocket.remote_address}")
            await self.context.send(msg.Error("Invalid message"))


async def handle_middleware_request(context, request):
    try:
        response = await REQUESTS[request.request_type](context, request)
        await context.send(response)
    except KeyError as error:
        logger.debug(f"{context}: request-type {error} is invalid")
        await context.send(msg.Error(f"request-type {error} is invalid", request.id))


async def handle_request(context, request):
    try:
        app = context.subscriptions[request.application]
        request.id, original_id = context.message_manager.new_id(), request.id
        await app.websocket.send(str(request))
        context.message_manager.add_request_await(context.websocket, original_id, request.id)

        logger.debug(
            f"Request from {context} forwarded to {request.application}")
    except KeyError:
        logger.debug(f"{context} didn't subscribe {request.application}")
        await context.send(msg.Error(f"{request.application} is not subscribed", request.id))


async def handle_event(context, event):
    try:
        subscribers = context.registration.subscribers
        if subscribers:
            await asyncio.wait([ws.send(str(event)) for ws in subscribers])
    except KeyError:
        logger.debug(f"{context} send event to the not self registered application {event.application}")
        await context.send(msg.Error(f"You have not {event.application} registered"))


async def handle_response(context, response):
    try:
        request = context.message_manager.request_awaits[response.id]
        request[2].set_result(response)
        response.id, manager_id = request[1], response.id
        await request[0].send(str(response))
    except KeyError:
        logger.debug(f"{response}: Request isn't anymore in request_awaits")
