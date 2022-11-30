# -*- coding: utf-8 -*-

import time
import random


class ExponentialBackoff:
    def __init__(self, maximum=4):
        self._exp = 0
        self._max = maximum
        self._reset_time = 2 ** maximum
        self._last_invocation = time.monotonic()

        self.rand = random.Random()
        self.rand.seed()

    def delay(self):
        invocation = time.monotonic()
        interval = invocation - self._last_invocation
        self._last_invocation = invocation

        if interval > self._reset_time:
            self._exp = 0

        delay = 2 ** self._exp + self.rand.randint(0, 1000) / 1000
        self._exp = min(self._exp + 1, self._max)

        return delay

    def reset(self):
        self._exp = 0
