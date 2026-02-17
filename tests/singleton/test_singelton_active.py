import utils_locked.singleton.singleton_helper as sh
import logging

from utils_locked.singleton import Singleton


@sh.enable_calls_on_active
class BareSingletonClass(Singleton):
    random_cls_attr = set()

    @Singleton.singleton_init
    def __init__(self):
        if hasattr(self, "call_count"):
            self.init_call_count += 1
        else:
            self.init_call_count = 1

    def get_call_count(self):
        return self.init_call_count

    @classmethod
    def classmethod_test(cls):
        return cls.random_cls_attr

    @staticmethod
    def staticmethod_test():
        return BareSingletonClass.random_cls_attr

    @classmethod
    def reset_singleton(cls):
        # TODO: put in singelton in general

        for wrapd, old in cls._wrapped_enable_methods.items():
            setattr(cls, wrapd, old)
        cls._wrapped_enable_methods.clear()

        cls._instance = None
        delattr(cls, "active")
        cls.random_cls_attr.clear()


def test_singleton_class_initialization():
    instance1 = BareSingletonClass()
    assert instance1.init_call_count == 1
    assert type(instance1) == BareSingletonClass
    assert BareSingletonClass.active == True

    BareSingletonClass.reset_singleton()

    assert not hasattr(BareSingletonClass, "active") \
           and BareSingletonClass._instance == None

    logging.warning(instance1._wrapped_enable_methods)

    bc2 = sh.enable_calls_on_active(BareSingletonClass, instance_based=True)

    instance2 = bc2()
    assert instance2.init_call_count == 1
    assert type(instance2) == BareSingletonClass
    assert BareSingletonClass.active == True


def test_singleton_class_method_test_not_instance_based(monkeypatch):
    """
    this test is for the case where the class is not instance based
    :return:
    """
    instance = BareSingletonClass()
    assert instance.get_call_count() == instance.init_call_count

    with monkeypatch.context() as m:
        m.setattr(BareSingletonClass, "active", False)
        assert instance.get_call_count() is None
        assert BareSingletonClass.active is False

    assert instance.get_call_count() == instance.init_call_count


def test_singleton_class_method_test_not_instance_based(monkeypatch):
    instance = BareSingletonClass()

    with monkeypatch.context() as m:
        m.setattr(instance, "active", False)
        assert instance.get_call_count() is not None
        assert BareSingletonClass.active is True


def test_singleton_class_classmethod_test(monkeypatch):
    unique_obj = object()
    with monkeypatch.context() as m:
        BareSingletonClass.random_cls_attr.add(unique_obj)
        assert unique_obj in BareSingletonClass.classmethod_test()
        m.setattr(BareSingletonClass, "active", False)
        breakpoint()
        assert BareSingletonClass.classmethod_test() is None

    assert unique_obj in BareSingletonClass.classmethod_test()
    breakpoint()


def test_singleton_class_staticmethod_test(monkeypatch):
    unique_obj = object()
    with monkeypatch.context() as m:
        BareSingletonClass.random_cls_attr.add(unique_obj)
        assert unique_obj in BareSingletonClass.staticmethod_test()
        m.setattr(BareSingletonClass, "active", False)
        assert BareSingletonClass.staticmethod_test() is None

    assert unique_obj in BareSingletonClass.staticmethod_test()
