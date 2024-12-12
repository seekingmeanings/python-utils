from racing.race_condition import LockedTracking
from typing import Any, List, Dict, Union
import os
import tomlkit
import logging
import functools
import copy


class EOI:
    """
    End of Iter
    """


class Config(LockedTracking):
    """
    a class that can handle config files and create subparts that are still linked to the parent

    """
    type KeyList = List[str]

    def __init__(self, config_file: str = None,
                 config_data=None,
                 parent=None,
                 parent_keys=None) -> None:
        # TODO get __file__ for init to get the global filepath here instead of the other class
        super().__init__()

        # TODO: sub config has extra logger
        self.lg = logging.getLogger(__name__)

        if config_file:
            self.lg.debug(f"using config file: {config_file}")

            self.edited_affix = ".edited"
            self._config_file = config_file
            self._edited_fp = self._config_file + self.edited_affix

            # load the config file
            self._config = self._load_config()

        else:
            self.lg.debug(f"using config data: {config_data}")

            self._config = config_data
            self.config_file = None

        self.parent = parent
        self.parent_keys = parent_keys or []

    @staticmethod
    def _ensure_tree_with_val_poss(func):
        # TODO: bad practice, keep one type
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            pass

    @staticmethod
    def _recurse_for_childs(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            """
            inputs: args = [list,] | [list, value]
            others: pk = parent_keys
            if input []:
                output: ([par1, par2, par_n],)

                if pk = []
                    output: []

            elif input [list,]
                output: ([par0, par1, par2, par_n, key0, key1],)

                if pk = []:
                    output: ([key0, key1],)

            elif input [list, value]:
                output: ([par0, par1, par2, par_n, key0, key1], value,)

                if pk = []:
                    output: ([key0, key1], value,)
            """

            def _call_with_potential_args(f, s, a, k):
                try:
                    logging.error(f"---- cl ---- {f}, {s}, {a}, {k}")
                    logging.error(f"||| nne ||| {[*[s.parent_keys, *a[:-1:]]]}")
                    logging.error(f"            {a[-1] if len(a) > 1 else EOI}")
                    logging.error(f"&&&& {(a[:-1] if len(a) > 1 else a)}")
                except (KeyError, TypeError):
                    pass

                return f(s, *a, **k)

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

    def _load_config(self) -> Dict:
        """
        load the config file

        if an edited version exists, load it instead
        :return:
        """
        if os.path.exists(self._edited_fp):
            with open(self._edited_fp, "r") as f:
                self.lg.info(f"loading config as toml from edited: {self._edited_fp}")
                return tomlkit.load(f)

        with open(self._config_file, "r") as f:
            self.lg.info(f"loading config as toml from original: {self._config_file}")
            return tomlkit.load(f)

    def apply_changes(self) -> None:
        """
        reload the config file itself
        :return:
        """
        with open(self._edited_fp, 'w') as f:
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
            keys = [keys, ]

        d = self._config
        for key in keys:
            d = d.get(key, None)
            if d is None:
                # key doesnt exist (on this level)
                raise KeyError
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
        with open(self._edited_fp, 'w') as f:
            self.lg.error(f"dumping shit to {self._edited_fp}")
            tomlkit.dump(self._config, f)

    @LockedTracking.locked_access
    @_recurse_for_childs
    def delete(self, keys: KeyList):
        tree = keys[:-1:]
        upper_stack_of_del = self.get(tree)
        upper_stack_of_del.pop(keys[-1])

        self.set(tree, upper_stack_of_del)

    @LockedTracking.locked_access
    def create_child_config(self, keys: KeyList):
        self.lg.debug(f"creating child from {keys}, subset is: {self.get(keys)}")
        try:
            subset = self.get(keys)
            if subset is None:
                raise RuntimeWarning("check implementation")
                subset = {}
                self.set(subset, keys)
        except AttributeError as e:
            # TODO: implement
            raise NotImplementedError(f"the keychain {keys} leads to a value") from e

        except KeyError as e:
            raise KeyError(f"keychain {keys} doesnt exist in {self}") from e

        else:
            return Config(
                # TODO: only need parent info, editing just on level 0
                config_data=subset,
                parent=self,
                parent_keys=keys
            )
