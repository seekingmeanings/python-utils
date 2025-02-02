import concurrent.futures
import random
import threading
import time
from pprint import pprint as pp
from typing import Dict, List, Tuple, Union

import pytest

from racing.parent_lock_class import LockedTracking

type WaitTuple = Tuple[Union[int, float], Union[int, float]]
type SetTo = int
type WaitList = List[Tuple[WaitTuple, SetTo]]
type ResultList = List[Dict[int, Dict[int, SetTo]]]


class LockedTestClass(LockedTracking):
    def __init__(self) -> None:
        super().__init__()

        self.test_var = 0

    @LockedTracking.locked_access
    def safe_test_method(self, wait: WaitTuple, set_to: SetTo) -> Dict[int, SetTo]:
        return self.test_method(wait, set_to)

    def test_method(self, wait: WaitTuple, set_to: SetTo) -> Dict[int, SetTo]:
        vals_over_time = {0: self.test_var}
        time.sleep(wait[0])
        vals_over_time[1] = self.test_var
        self.test_var = set_to
        time.sleep(wait[1])
        vals_over_time[2] = self.test_var
        return vals_over_time

    def return_with_set_to(
        self, wait: WaitTuple, set_to: SetTo, safe=True
    ) -> dict[int, dict[int, SetTo]]:
        self.lg.debug(f"Setting to: {set_to}")
        return (
            {set_to: self.test_method(wait, set_to)}
            if not safe
            else {set_to: self.safe_test_method(wait, set_to)}
        )

    def reset(self):
        self.test_var = 0


@pytest.fixture
def instance_of_test_class():
    return LockedTestClass()


def generate_random_waitlist():
    """
    thanks chatgpt
    :return:
    """

    def biased_random_float():
        """Generates a random float value with a bias towards smaller numbers."""
        return round(random.expovariate(1 / 0.5), 2)  # Smaller numbers are more likely

    num_tuples = random.randint(10, 30)
    wait_list = []
    used_values = set()

    for _ in range(num_tuples):
        while True:
            base_value = biased_random_float()
            base_value = max(
                0.01, min(5.0, base_value)
            )  # Clamp base value between 0.01 and 5.0
            variation = random.uniform(
                -0.1, 0.1
            )  # Small variation to keep values close together
            nested_tuple = (base_value, max(0.01, min(5.0, base_value + variation)))
            outer_int = max(
                1, int(min(5.0, min(nested_tuple)) * 100)
            )  # Convert smallest float to int (scaled)

            if outer_int not in used_values:
                used_values.add(outer_int)
                wait_list.append((nested_tuple, outer_int))
                break

    return wait_list


@pytest.mark.parametrize("safe", [True, False])
@pytest.mark.parametrize(
    "wait_list",
    [
        [
            ((0.5, 0.5), 5),
            ((0.1, 0.1), 1),
            ((0.2, 0.2), 2),
        ],
        generate_random_waitlist(),
    ],
)
def test_locking(instance_of_test_class, safe: bool, wait_list: WaitList):
    inst = instance_of_test_class

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(wait_list)) as executor:
        futures = []
        for wait, set_to in wait_list:
            print(f"Setting to: {set_to}")
            futures.append(executor.submit(inst.return_with_set_to, wait, set_to, safe))
            # have some random delay
            # this fails cause the lock time is after calling so the order changes
            # should not be a problem tho
            #
            # time.sleep(random.uniform(0.05, 2))

        results: ResultList = [
            future.result() for future in concurrent.futures.as_completed(futures)
        ]

    try:
        # Check the outputs
        assert len(results) == len(wait_list)

        # has to be in call order (they should block in this order)
        list_of_set_to = [set_to for _, set_to in wait_list]
        list_of_result_keys = [key for result in results for key in result.keys()]

        assert len(list_of_result_keys) == len(list_of_set_to)

        assert list_of_set_to == list_of_result_keys
        assert results[0][list_of_set_to[0]][0] == 0

        for set_to, result in zip([set_to for _, set_to in wait_list], results):
            assert result[set_to][0] == result[set_to][1]
            assert result[set_to][2] == set_to

    except AssertionError as e:
        if safe:
            raise e
        else:
            # thats what we want anyway, it has to fail when not safe
            pass

    else:
        if not safe:
            raise AssertionError("Should fail and not work")

    # reset the test_var
    inst.reset()
    assert inst.test_var == 0
