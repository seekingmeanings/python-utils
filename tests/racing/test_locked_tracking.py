from racing.parent_lock_class import LockedTracking
import time
import pytest
import threading
import concurrent.futures

from typing import Tuple


class TestClass(LockedTracking):
    def __init__(self) -> None:
        super().__init__()

        self.test_var = 0

    @LockedTracking.locked_access
    def test_method(self, wait: Tuple[int, int], set_to: int) -> int:
        time.sleep(wait[0])
        self.test_var = set_to
        time.sleep(wait[1])
        return self.test_var


def test_locking():
    inst = TestClass()
    wait_list = [1,2,3,4]

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(wait_list)) as executer:
        executer.map(inst.test_method, wait_list)