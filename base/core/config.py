#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Models for our configuration because marshaling is a cool thing to do and looks awesome.
"""
import abc
import dataclasses
import os
import typing

import dacite

ThisImplT = typing.TypeVar("ThisImplT")


def hidden_field(**kwargs):
    """Makes the field not show up in a REPR."""
    return dataclasses.field(repr=False, **kwargs)


def get_postgres_password_from_environment():
    return os.environ["POSTGRES_PASSWORD"]


class BaseModel(typing.Generic[ThisImplT], metaclass=abc.ABCMeta):
    """Base marshalling functionality for any model we use with Dacite."""

    @classmethod
    def from_dict(cls: typing.Type[ThisImplT], obj: dict) -> ThisImplT:
        return dacite.from_dict(cls, obj)

    def to_dict(self):
        assert dataclasses.is_dataclass(self)
        # noinspection PyDataclass
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True)
class BotConfig(BaseModel):
    command_prefix: str
    token: str = hidden_field()

    # Optional list of extensions to NOT load.
    blacklist_extensions: typing.List[str] = dataclasses.field(default_factory=list)


@dataclasses.dataclass(frozen=True)
class PostgresConfig(BaseModel):
    password: str = hidden_field(default_factory=get_postgres_password_from_environment)
    host: str = "localhost"
    port: int = 5432
    user: str = "postgres"
    database: str = "postgres"


@dataclasses.dataclass(frozen=True)
class Logging(BaseModel):
    level: str = "INFO"


@dataclasses.dataclass(frozen=True)
class Flower(BaseModel):
    url: str
    value: str
    emoji: str


@dataclasses.dataclass(frozen=True)
class Config(BaseModel):
    bot: BotConfig
    logging: Logging
    postgres: PostgresConfig
    categories: typing.Dict[str, typing.Optional[int]]
    channels: typing.Dict[str, typing.Optional[int]]
    roles: typing.Dict[str, typing.Optional[int]]
    maxes: typing.Dict[int, typing.Optional[int]]
    flowers: typing.Dict[str, typing.Optional[Flower]]
