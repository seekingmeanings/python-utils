import copy
import functools
import logging
import os
from typing import Any, Callable, Dict, List, Self, Union

import tomlkit

from utils_locked.racing.parent_lock_class import LockedTracking


class EOI:
    """
    End of Iter
    """


def prevent_orphan_lookup(private_whitelist: List):
    """
    a wrapper that prevents an orphan and empty config from being accessed
    :param private_whitelist:
    :return:
    """

    def class_decorator(cls):
        for attr_name in dir(cls):
            if callable(getattr(cls, attr_name)) and (not attr_name.startswith("__") or attr_name in private_whitelist):
                setattr(cls, attr_name, _raise_error_on_empty_config(getattr(cls, attr_name)))
        return cls

    return class_decorator


def _raise_error_on_empty_config(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if self._empty:
            raise NoConfigError()
        return func(self, *args, **kwargs)

    return wrapper


class NoConfigError(Exception):
    """Custom error if there was no config file loaded for whatever reason"""

    def __init__(self, message="No config file loaded"):
        self.message = message
        super().__init__(self.message)


class KeychainAccessError(Exception):
    """Custom error for when there's an issue accessing a keychain value."""

    def __init__(self, keys, message="Unable to access value with the provided keychain"):
        self.keys = keys
        self.message = message
        super().__init__(self.message)


class KeychainEndError(KeychainAccessError):
    """Custom error for when there's an issue accessing a keychain value."""

    def __init__(self, keys, message="End of keychain reached"):
        self.keys = keys
        self.message = message
        super().__init__(self.keys, self.message)


@prevent_orphan_lookup(["__getitem__", ])
class Config(LockedTracking):
    # TODO: generalise conf types
    """
    a class that can handle config files and create subparts that are still linked to the parent

    """

    type KeyList = List[str]

    def __init__(
            self, config_file: str = None, config_data=None, parent=None, parent_keys=None, active_repr=False,
    ) -> None:
        # TODO get __file__ for init to get the global filepath here instead of the other class
        # WARNING: this is only temporary, need fixes
        super().__init__(ignore_inter_thread=True)

        # TODO: sub config has extra logger

        self.lg = logging.getLogger(f"{__name__}")
        self._empty = False

        self._repr = active_repr

        if config_file:
            # update logger for easier debugging
            self.lg = logging.getLogger(f"{__name__}: {config_file}")

            self.edited_affix = ".edited"
            self._config_file = config_file
            self._edited_fp = self._config_file + self.edited_affix

            # load the config file
            self._config = self._load_config()

        elif not parent and not config_data:
            self.lg.warning("no config file or data provided and seems to be orphan")
            self._empty = True

        else:

            self.lg.debug(f"using config data: {config_data}")

            self._config = config_data
            self.config_file = None

        self.parent = parent
        self.parent_keys = parent_keys or []



    @staticmethod
    def _ensure_tree_with_val_poss(func):
        # TODO: make str possible (at least for get)
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            pass

    @staticmethod
    def _recurse_for_childs(func) -> Callable:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            def _get_modulated_args(parent_keys, args) -> List:
                # TODO: check
                if not args:
                    if not parent_keys:
                        return []
                    else:
                        return (parent_keys,)

                # If args contains only a list
                elif len(args) == 1 and isinstance(args[0], list):
                    combined_output = parent_keys + args[0]
                    if not parent_keys:
                        return args[0]
                    else:
                        return (combined_output,)

                # If args contains a list and a value
                elif len(args) == 2 and isinstance(args[0], list):
                    combined_output = parent_keys + args[0]
                    value = args[1]
                    if not parent_keys:
                        return (args[0], value)
                    else:
                        return (combined_output, value)

            if self.parent:
                return getattr(self.parent, func.__name__)(
                    *_get_modulated_args(self.parent_keys, args),
                    **kwargs,
                )
            return func(self, *args, **kwargs)

        return wrapper

    def __getitem__(self, key: Any) -> Any:
        """
        warning: returned children have _repr set to True, can disable tho
        :param key:
        :return:
        """
        if not isinstance(key, list):
            key = [key]
        # we have to check what to return
        child = self.create_child_config(key)
        self.lg.debug(f"returning child: {child}")
        # add repr for future childs
        child._repr = True
        return child

    def __repr__(self):
        """
        only return when its active (with getitem)
        :return:
        """
        if self._repr:
            return repr(self.get())
        return super().__repr__()

    def _load_config(self) -> Dict:
        """
        load the config file

        if an edited version exists, load it instead
        :return:
        """
        if os.path.exists(self._edited_fp):
            with open(self._edited_fp, "r") as f:
                self.lg.debug(f"loading config as toml from edited: {self._edited_fp}")
                return tomlkit.load(f)

        with open(self._config_file, "r") as f:
            self.lg.debug(f"loading config as toml from original: {self._config_file}")
            return tomlkit.load(f)

    def apply_changes(self) -> None:
        """
        reload the config file itself
        :return:
        """
        with open(self._edited_fp, "w") as f:
            tomlkit.dump(self._config, f)

    @LockedTracking.locked_access
    @_recurse_for_childs
    def get(self, keys: KeyList = None) -> Union[Dict, Any]:
        """
        get the config stack
        :return: get the stack
        """
        # TODO: put in other wrapper
        if keys is None:
            keys = []
        elif isinstance(keys, str):
            raise RuntimeWarning("put keys in list")
            # TODO: get set compatibility
            keys = [
                keys,
            ]

        d = self._config
        for key in keys:
            if not isinstance(d, dict):
                raise KeychainEndError(keys=keys)
            d = d.get(key, None)
            if d is None:
                # key doesnt exist (on this level)
                raise KeyError(f"key chain: {keys} not found")
        return d

    @LockedTracking.locked_access
    @_recurse_for_childs
    def set(self, keys: KeyList, value: Any) -> None:
        """
        set a value in the config stack

        after that, the config file will be updated
        there will be a new file with the ending .edited
        that will be loaded instead of the original file
        to not overwrite the original file
        :return:
        """
        d = self._config
        for key in keys[:-1]:
            if key not in d:
                d[key] = {}
            d = d[key]
        d[keys[-1]] = value

        # safe n shit
        with open(self._edited_fp, "w") as f:
            self.lg.error(f"dumping shit to {self._edited_fp}")
            tomlkit.dump(self._config, f)

    @LockedTracking.locked_access
    @_recurse_for_childs
    def delete(self, keys: KeyList) -> None:
        tree = keys[:-1:]
        upper_stack_of_del = self.get(tree)
        upper_stack_of_del.pop(keys[-1])

        self.set(tree, upper_stack_of_del)

    @LockedTracking.locked_access
    def create_child_config(self, keys: KeyList) -> Self:
        # TODO: implement list childs with index and not just keys (the indexes have to be remarked in the keys tho
        self.lg.debug(f"creating child from {keys}, subset is: {self.get(keys)}")
        try:
            subset = self.get(keys)
            if subset is None:
                raise RuntimeWarning("check implementation")
                subset = {}
                self.set(subset, keys)
        except AttributeError as e:
            raise KeychainEndError(keys=keys)

        except KeyError as e:
            raise KeyError(f"keychain {keys} doesnt exist in {self}") from e

        else:
            return Config(
                # TODO: only need parent info, editing just on level 0
                config_data=subset,
                parent=self,
                parent_keys=keys,
            )
