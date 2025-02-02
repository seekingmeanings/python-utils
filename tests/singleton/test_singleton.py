import pytest
from singleton.singleton import Singleton


class Base:
    """Parent class with its own __new__ method."""

    new_called = False  # Class-level attribute to track calls

    def __new__(cls, *args, **kwargs):
        Base.new_called = True  # Mark that __new__ was called
        return super().__new__(cls)


class DirectChild(Singleton):
    """Parent class with its own __new__ method."""

    new_called = False  # Class-level attribute to track calls

    def __new__(cls, *args, **kwargs):
        DirectChild.new_called = True  # Mark that __new__ was called
        return super().__new__(cls)


class Derived(Singleton, Base):
    """Derived class inheriting from Singleton and Base."""

    pass


def test_singleton_with_derived_parent_new():
    """Test that Singleton respects parent __new__ method."""

    # Reset the tracking variable
    Base.new_called = False

    # Create first instance
    instance1 = Derived()

    # Create second instance
    instance2 = Derived()

    # Assert the parent class __new__ was called
    assert Base.new_called, "Base class __new__ was not called!"

    # Assert that Singleton property holds
    assert instance1 is instance2, "Singleton property violated!"


def test_singleton_as_direct_parent_new():
    """Test that Singleton respects parent __new__ method."""

    assert not DirectChild.new_called

    # Create first instance
    instance1 = DirectChild()

    # Create second instance
    instance2 = DirectChild()

    # Assert the parent class __new__ was called
    assert DirectChild.new_called, "Base class __new__ was not called!"

    # Assert that Singleton property holds
    assert instance1 is instance2, "Singleton property violated!"
