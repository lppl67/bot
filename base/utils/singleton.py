#!/usr/bin/env python3
# -*- coding: utf-8 -*-


"""
Singleton pattern implementation for creating unique one-instance objects
from classes on demand.
"""

__all__ = ("SingletonMeta", "Singleton")


def _singleton_repr(t: type):
    return f"<{t.__name__} Singleton>"


class SingletonMeta(type):
    """
    Metaclass that enforces the Singleton pattern. Useful for specialising
    sentinel objects, et cetera.
    """

    __singletons = {}

    def __call__(cls):
        if cls in cls.__singletons:
            return cls.__singletons[cls]
        else:
            singleton = super(SingletonMeta, cls).__call__()
            cls.__singletons[cls] = singleton
            return singleton

    def __repr__(cls):
        return _singleton_repr(cls)

    def __eq__(cls, other):
        if isinstance(type(other), cls):
            return True
        elif other is cls:
            return True
        else:
            return False

    def __hash__(cls):
        return super().__hash__()

    __str__ = __repr__


class Singleton(metaclass=SingletonMeta):
    """Less verbose way of implementing a singleton class."""

    __slots__ = ()

    def __repr__(self):
        return _singleton_repr(type(self))

    __str__ = __repr__

    def __eq__(self, other):
        if isinstance(other, type(self)):
            return True
        elif other is self:
            return True
        else:
            return False
