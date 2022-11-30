# -*- coding: utf-8 -*-

from misc.message import Event


async def unsubscribed_from(websocket, name):
    await websocket.send(str(Event(update_type='UnsubscribedFrom', name=name)))

EVENTS = {'UnsubscribedFrom': unsubscribed_from}
