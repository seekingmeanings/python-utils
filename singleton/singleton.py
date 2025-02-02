import importlib

from typing import Union, List

import logging


class Singleton:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            # revive attr for tagging

            # cls._instance = super(Singleton, cls).__new__(cls)
            cls._instance = super().__new__(cls, *args, **kwargs)

        return cls._instance

    @staticmethod
    def singleton_init(init_func):
        def wrapper(self, *args, **kwargs):
            if not hasattr(self, '_initialized'):
                init_func(self, *args, **kwargs)

                # can't use _instance cause its already been set at that point
                self._initialized = True

        return wrapper

    @singleton_init
    def __init__(self):
        self.lg = logging.getLogger(self.__class__.__name__)
        pass


# TODO: make a wrapper version?
