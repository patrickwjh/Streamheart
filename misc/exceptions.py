# -*- coding: utf-8 -*-


class MessageError(ValueError):
    """
    Base message error.
    """
    def __init__(self, message, message_id=None):
        super().__init__(message)
        self.message_id = message_id


class InvalidMessageError(MessageError):
    """
    Raised if the message doesn't match the protocol.
    """


class InvalidRequestError(MessageError):
    """
    Raised if request message base fields are missing.
    """


class InvalidResponseError(MessageError):
    """
    Raised if response message base fields are missing.
    """


class InvalidEventError(MessageError):
    """
    Raised if event message base fields are missing.
    """


class RegisterException(Exception):
    """
    Raised if a client register an application that's already registered.
    """


class UnregisterException(Exception):
    """
    Raised if a client unregister a application that's not registered.
    """


class SubscribeException(Exception):
    """
    Raised if a client tries to subscribe to a not exist or already subscribed application.
    """


class UnsubscribeException(Exception):
    """
    Raised if a client subscribes an application that already subscribed.
    """


class ReconnectTimeout(Exception):
    """
    Raised if maximum of reconnect tries reached.
    """


class RequestTimeout(Exception):
    """
    Raised if no response for a request received within the maximum waiting time
    """
    def __init__(self, message_id=None):
        super().__init__()
        self.message_id = message_id


class ResponseStatusError(Exception):
    """
    Raised if the response status is error
    """
    def __init__(self, error, message_id):
        super().__init__(error)
        self.message_id = message_id


class ConfigError(Exception):
    """
    Raised if the config file is invalid
    """