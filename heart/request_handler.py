# -*- coding: utf-8 -*-

import logging
from misc import exceptions, message as msg

logger = logging.getLogger(__name__)


async def register(context, request):
    response = msg.Error("Request error")

    try:
        name = request.additionals['name']
        context.add_application(name)
        response = msg.Ok(request.id)
        logger.debug(f"{name} registered successfully from {context}")
    except KeyError as error:
        logger.debug(f"Missing additional field {error}")
        response = msg.Error(f"Missing additional field: {error}", request.id)
    except exceptions.RegisterException as error:
        logger.debug(f"{context}: {error}")
        response = msg.Error(str(error), request.id)
    finally:
        return response


async def unregister(context, request):
    response = msg.Error("Request error")

    try:
        name = request.additionals['name']
        await context.remove_application(name)
        response = msg.Ok(request.id)
        logger.debug(f"{name} unregistered successfully from {context}")
    except KeyError as error:
        logger.debug(f"Missing additional field {error}")
        response = msg.Error(f"Missing additional field: {error}", request.id)
    except exceptions.UnregisterException as error:
        logger.debug(f"{context}: {error}")
        response = msg.Error(str(error), request.id)
    finally:
        return response


async def subscribe(context, request):
    response = msg.Error("Request error")

    try:
        name = request.additionals['name']
        context.add_subscription(name)
        response = msg.Ok(request.id)
        logger.debug(f"{name} subscribed successfully from {context}")
    except KeyError as error:
        logger.debug(f"Missing additional field {error}")
        response = msg.Error(f"Missing additional field: {error}", request.id)
    except exceptions.SubscribeException as error:
        logger.debug(f"{context}: {error}")
        response = msg.Error(str(error), request.id)
    finally:
        return response


async def unsubscribe(context, request):
    response = msg.Error("Request error")

    try:
        name = request.additionals['name']
        context.remove_subscription(name)
        response = msg.Ok(request.id)
        logger.debug(f"{name} unsubscribed successfully from {context}")
    except KeyError as error:
        logger.debug(f"Missing additional field {error}")
        response = msg.Error(f"Missing additional field: {error}", request.id)
    except exceptions.UnsubscribeException as error:
        logger.debug(f"{context}: {error}")
        response = msg.Error(str(error), request.id)
    finally:
        return response


REQUESTS = {'Register': register, 'Unregister': unregister, 'Subscribe': subscribe, 'Unsubscribe': unsubscribe}
