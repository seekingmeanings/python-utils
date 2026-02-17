import logging

#from .toml_config import Config
from ..racing.parent_lock_class import LockedTracking

class Config:
    pass

class Schema(LockedTracking):
    """
    wraps a config for schema usage??,
    just have to shadow the write method
    """

    def __init__(self, schema: str):
        super().__init__()

        self.lg = logging.getLogger(f"{__name__}")

        self.schema = Config(schema)


    def check(self):
        pass




def check_schema():
    """
    check a chema itself with the integrated tool

    :return:
    """
    pass