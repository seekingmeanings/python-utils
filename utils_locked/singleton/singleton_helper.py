import inspect

from typing import Callable, Type, List

import logging


def _pass_on_not_active_considering_instance_w_fallback_wrapper(method):
    """
    this is a wrapper that will only pass on the method if the instance has an active attribute
    with fallback to class if possible
    :param method:
    :return: Callable
    """
    lg = logging.getLogger(f"wrapper for {method.__qualname__}")

    def wrapper(*args, **kwargs):
        if hasattr(method, '__self__'):

            if method.__self__.active:
                lg.debug(f" allow: active")
                return method(*args, **kwargs)

            # DOCU: just don't execute the function
            # WARNING: some stuff will be completely not working???
            lg.debug(f" skip: not active")

        else:
            if isinstance(method, staticmethod):
                lg.debug(f" allow: staticmethod")
                return method(*args, **kwargs)

            # we have to make sure its not just an init call without having __self__ attribute (first call)
            # so we have to double check the class for an active attribute

            # DOCU: yanky way to get the class of the method, but HELP no other way when no instance exists

            try:
                # breakpoint()
                unwrapped_method = method
                # unwrap the function if its wrapped
                while hasattr(unwrapped_method, "__wrapped__"):
                    unwrapped_method = unwrapped_method.__wrapped__

                if unwrapped_method.__globals__[unwrapped_method.__qualname__.split(".")[0]].active:
                    lg.debug(f" allow: active, no __self__")
                    return method(*args, **kwargs)
            except AttributeError as e:
                raise RuntimeError(f"are you trying to wrap a wrapped singleton?") from e

            lg.debug(f" skip: not active, no __self__")

    return wrapper


def _pass_on_not_active_in_class_wrapper(method: Callable, container_class: Type) -> Callable:
    """
    this is a wrapper that will only pass on the method if the class has an active attribute
    not the instance??????????????????
    :param method:
    :param container_class:
    :return: wrapped method
    """
    lg = logging.getLogger(f"wrapper for {method} in {container_class.__name__}")

    def wrapper(*args, **kwargs):
        if container_class.active:
            lg.debug(f" allow")
            return method(*args, **kwargs)

        lg.debug(f" refuse")

    return wrapper


def enable_calls_on_active(cls: Type, instance_based: bool = False, restore=True, no_wrap: List | None = None) -> Type:
    """
    this decorator can deactivate all methods in a class based of the active attribute

    cls.active is set to True if not already set

    In the instance based mode the active attribute is checked on the instance itself
    and static methods are allowed to always pass.

    :param restore:
    :param no_wrap: list of methods to ignore
    :param instance_based: where the active is coming from
    :param cls:
    :return: cls with wrapped methods
    """
    lg = logging.getLogger(f"ecoa wrapper for class {cls.__name__}")

    if no_wrap is None:
        no_wrap = []

    if not hasattr(cls, 'active'):
        cls.active = True
        if restore:
            cls._wrapped_enable_methods = {}
        # TODO: do i need to trigger something on change?? (could use property)

    for attr_name, attr in cls.__dict__.items():
        if attr_name in no_wrap:
            lg.debug(f"skipping {attr_name} type({type(attr)}) because its in no_wrap")
            continue

        breakpoint()

        if callable(attr):
            lg.debug(f"trying to wrap: {attr}")
            old_func = attr
            if instance_based:
                # HELP: can i put this info somewhere available in the class?
                # TODO: make meta info available in the class
                if isinstance(old_func, staticmethod) or not hasattr(old_func, '__qualname__'):
                    # this is a staticmethod
                    lg.debug(f"skipping staticmethod {attr_name} because instance_based is set")
                    continue
                wrapped_func = _pass_on_not_active_considering_instance_w_fallback_wrapper(old_func)
            else:
                wrapped_func = _pass_on_not_active_in_class_wrapper(old_func, cls)

            setattr(cls, attr_name, wrapped_func)

            if restore:
                cls._wrapped_enable_methods[attr_name] = old_func

            lg.debug(f"wrapped {attr_name}")
        elif hasattr(attr, "__func__"):
            # breakpoint()
            logging.warning(f"found a classmethod most likely not wrapping???: {attr}")

    return cls
