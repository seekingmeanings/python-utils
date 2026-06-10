import logging

import lib.tomlkit.items
from utils_locked.config.toml_config import Config
from utils_locked.racing.parent_lock_class import LockedTracking

import sys

class Schema(LockedTracking):
    """
    wraps a config for schema usage??,
    just have to shadow the write method
    """

    def __init__(self, schema: str):
        super().__init__()

        self.lg = logging.getLogger(f"{__name__}")

        self.schema_l = Config(schema)


    def check(self, toml_file) -> bool:
        cft = Config(toml_file)

        cfto = cft.get()

        for obj in self.schema_l.get(["ifo"]):
            if obj["required"]:
                assert obj["key"] in cfto

                print(type(cfto[obj["key"]]))
                assert isinstance(cfto[obj["key"]], int)

        return True

    def dump_schema(self) -> str:
        return self.schema_l.dump_file()


def check_schema():
    """
    check a chema itself with the integrated tool

    :return:
    """
    pass


if __name__ == "__main__":
    print("--- test")

    s = Schema(sys.argv[1])

    s.check(sys.argv[2])