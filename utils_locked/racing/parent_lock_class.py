import logging
from functools import wraps
from threading import Lock, RLock, Condition
from time import gmtime


class LockedTracking:
    def __init__(self, ignore_inter_thread: bool = False) -> None:
        """

        :param ignore_inter_thread: use RLock, not blocking for same-thread requests
        """

        self.lg = logging.getLogger(__name__)

        self._last_access = None
        self._lock = RLock() if ignore_inter_thread else Condition()

    # TODO: keep property decorators alive
    @staticmethod
    def locked_access(_func=None, *, track=True):
        def exec_wrap(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                wrapped_self = args[0]
                wrapped_self.lg.debug(f"acquiring lock for: {func.__name__}")
                with wrapped_self._lock:
                    wrapped_self.lg.debug(f"acquired lock for: {func.__name__}")
                    if track:
                        wrapped_self.last_access = gmtime()
                    return func(*args, **kwargs)

            return wrapper

        if _func is None:
            return exec_wrap
        else:
            return exec_wrap(_func)

    @locked_access(track=False)
    def last_access(self):
        return self._last_access
