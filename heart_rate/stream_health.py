# -*- coding: utf-8 -*-

from enum import Enum


class StreamHealth:
    def __init__(self):
        self.status = Offline(self)


class Status:
    def __init__(self, context):
        self.context = context
        self.better = self.Counter()
        self.worse = self.Counter()

    def reset_counter(self):
        self.better.value = 0
        self.worse.value = 0

    class Counter:
        def __init__(self, maximum=6):
            self.value = 0
            self.max = maximum

        def increment(self):
            self.value += 1

            if self.value >= self.max:
                self.value = 0
                return True

            return False


class Offline(Status):
    def __init__(self, context):
        super().__init__(context)
        self.state = State.OFFLINE

    def update(self, state):
        if state is State.CRITICAL:
            if self.better.increment():
                self.context.status = Critical(self.context)
        elif state is State.LOW:
            if self.better.increment():
                self.context.status = Low(self.context)
        elif state is State.STABLE:
            if self.better.increment():
                self.context.status = Stable(self.context)
        else:
            self.reset_counter()


class Critical(Status):
    def __init__(self, context):
        super().__init__(context)
        self.state = State.CRITICAL

    def update(self, state):
        if state is State.OFFLINE:
            self.context.status = Offline(self.context)
        elif state is State.LOW:
            self.worse.value = 0
            if self.better.increment():
                self.context.status = Low(self.context)
        elif state is State.STABLE:
            self.worse.value = 0
            if self.better.increment():
                self.context.status = Stable(self.context)
        else:
            self.reset_counter()


class Low(Status):
    def __init__(self, context):
        super().__init__(context)
        self.state = State.LOW

    def update(self, state):
        if state is State.OFFLINE:
            self.context.status = Offline(self.context)
        elif state is State.CRITICAL:
            self.better.value = 0
            if self.worse.increment():
                self.context.status = Critical(self.context)
        elif state is State.STABLE:
            self.worse.value = 0
            if self.better.increment():
                self.context.status = Stable(self.context)
        else:
            self.reset_counter()


class Stable(Status):
    def __init__(self, context):
        super().__init__(context)
        self.state = State.STABLE

    def update(self, state):
        if state is State.OFFLINE:
            self.context.status = Offline(self.context)
        elif state is State.CRITICAL:
            if self.worse.increment():
                self.context.status = Critical(self.context)
        elif state is State.LOW:
            if self.worse.increment():
                self.context.status = Low(self.context)
        else:
            self.reset_counter()


class State(str, Enum):
    ERROR = 'ERROR'
    OFFLINE = 'OFFLINE'
    CRITICAL = 'CRITICAL'
    LOW = 'LOW'
    STABLE = 'STABLE'
