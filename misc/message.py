# -*- coding: utf-8 -*-

import json
from enum import Enum
from misc import exceptions

REQUEST_FIELDS = ('application', 'request-type', 'message-id')
RESPONSE_FIELDS = ('message-id', 'status', 'error')
EVENT_FIELDS = ('update-type',)


class Status(str, Enum):
    ERROR = 'error'
    OK = 'ok'


def check_message(message):
    msg_class = None

    try:
        try:
            Event.check(message)
            return Event(message=message, check=False)
        except exceptions.InvalidEventError:
            pass
        try:
            Request.check(message)
            return Request(message=message, check=False)
        except exceptions.InvalidRequestError:
            pass
        try:
            Response.check(message)
            return Response(message=message, check=False)
        except exceptions.InvalidResponseError:
            pass
    except exceptions.InvalidMessageError:
        return msg_class

    return msg_class


class Request:
    def __init__(self, application: str = None, request_type: str = None, message_id: int = None, message=None,
                 check=True, **kwargs):
        self.application = application
        self.request_type = request_type
        self.id = message_id
        self.additionals = kwargs

        if message:
            self.parse(message, check)
        else:
            if not self.application or not self.request_type or (not self.id and self.id != 0):
                raise exceptions.InvalidRequestError("Required request field is not set", self.id)

    def parse(self, message, check):
        if check:
            message = Request.check(message)
        else:
            message = json.loads(message)

        self.application = message.pop(REQUEST_FIELDS[0])
        self.request_type = message.pop(REQUEST_FIELDS[1])
        self.id = message.pop(REQUEST_FIELDS[2])
        self.additionals = message

    @staticmethod
    def check(message):
        try:
            message = json.loads(message)
        except json.JSONDecodeError:
            raise exceptions.InvalidMessageError("Request is not a JSON object")

        application, request_type, message_id = None, None, None

        try:
            application = message[REQUEST_FIELDS[0]]
            request_type = message[REQUEST_FIELDS[1]]
            message_id = message[REQUEST_FIELDS[2]]
        except KeyError as key_error:
            raise exceptions.InvalidRequestError(f"Request doesn't match the protocol. Missing field: {key_error}",
                                                 message_id)

        if not application or not request_type or (not message_id and message_id != 0):
            raise exceptions.InvalidRequestError("Required request field is not set", message_id)

        return message

    def __repr__(self):
        return json.dumps(
            {**{REQUEST_FIELDS[0]: self.application, REQUEST_FIELDS[1]: self.request_type, REQUEST_FIELDS[2]: self.id},
             **self.additionals})


class Response:
    def __init__(self, message_id: int = None, status: Status = None, error: str = None, message=None, check=True,
                 **kwargs):
        self.id = message_id
        self.status = status
        self.error = error if error else ""
        self.additionals = kwargs

        if message:
            self.parse(message, check)
        else:
            if self.status is not Status.OK and self.status is not Status.ERROR:
                raise ValueError("status must be from class Status")

            if self.status is Status.OK and (not self.id and self.id != 0):
                raise ValueError("message-id must be set with Status.OK")

    def parse(self, message, check):
        if check:
            message = Response.check(message)
        else:
            message = json.loads(message)

        self.id = int(message.pop(RESPONSE_FIELDS[0]))

        if type(self.id) is str and self.id != "":
            try:
                self.id = int(self.id)
            except ValueError as error:
                raise exceptions.InvalidResponseError(error, self.id)

        self.status = Status[message.pop(RESPONSE_FIELDS[1]).upper()]

        if self.status == Status.ERROR:
            self.error = message.pop(RESPONSE_FIELDS[2])
        self.additionals = message

    @staticmethod
    def check(message):
        try:
            message = json.loads(message)
        except json.JSONDecodeError:
            raise exceptions.InvalidMessageError("Response is not a JSON object")

        message_id, status, error = None, None, None

        try:
            message_id = message[RESPONSE_FIELDS[0]]

            if type(message_id) is str and message_id != "":
                try:
                    message_id = int(message_id)
                except ValueError as error:
                    raise exceptions.InvalidResponseError(error, message_id)

            status = message[RESPONSE_FIELDS[1]]

            if status == Status.ERROR:
                error = message[RESPONSE_FIELDS[2]]
        except KeyError as key_error:
            raise exceptions.InvalidResponseError(f"Response doesn't match the protocol. Missing field: {key_error}",
                                                  message_id)

        if not status:
            raise exceptions.InvalidResponseError("Response status field is not set", message_id)

        if status == Status.OK and (not message_id and message_id != 0):
            raise exceptions.InvalidResponseError("Response message-id field is not set", message_id)

        return message

    def __repr__(self):
        return json.dumps(
            {**{RESPONSE_FIELDS[0]: self.id, RESPONSE_FIELDS[1]: self.status, RESPONSE_FIELDS[2]: self.error},
             **self.additionals})


class Event:
    def __init__(self, update_type: str = None, message=None, check=True, **kwargs):
        self.update_type = update_type
        self.additionals = kwargs

        if message:
            self.parse(message, check)
        else:
            if not self.update_type:
                raise exceptions.InvalidEventError("Event doesn't match the protocol")

    def parse(self, message, check):
        if check:
            message = Event.check(message)
        else:
            message = json.loads(message)

        self.update_type = message.pop(EVENT_FIELDS[0])
        self.additionals = message

    @staticmethod
    def check(message):
        try:
            message = json.loads(message)
        except json.JSONDecodeError:
            raise exceptions.InvalidMessageError("Event is not a JSON object")

        update_type = None

        try:
            update_type = message[EVENT_FIELDS[0]]
        except KeyError as key_error:
            raise exceptions.InvalidEventError(f"Event doesn't match the protocol. Missing field: {key_error}")

        if not update_type:
            raise exceptions.InvalidEventError("Event update-type field is not set")

        return message

    def __repr__(self):
        return json.dumps(
            {**{EVENT_FIELDS[0]: self.update_type}, **self.additionals})


class Ok(Response):
    def __init__(self, message_id: int, **kwargs):
        super().__init__(message_id, Status.OK, **kwargs)


class Error(Response):
    def __init__(self, error_msg: str, message_id: int = None):
        super().__init__(message_id, Status.ERROR, error_msg)
