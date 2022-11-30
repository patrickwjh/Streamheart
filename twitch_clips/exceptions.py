# -*- coding: utf-8 -*-


class ClipUrlError(Exception):
    """
    Raised if the clip url can't be parsed
    """
    def __init__(self, message, url):
        super().__init__(message)
        self.url = url
