#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging

import asyncpg
from discord.ext import commands

from base.utils.premade_messages import token_conversion_message
from . import client


class BaseCog(commands.Cog):
    def __init__(self, bot):
        self.logger = logging.getLogger(type(self).__module__ + "." + type(self).__name__)
        self.bot: client.Client = bot

    @property
    def database(self) -> asyncpg.pool.Pool:
        return self.bot.database

    @property
    def sql_cache(self):
        return self.bot.sql_cache

    @property
    def config(self):
        return self.bot.config

    @staticmethod
    def plur_simple(cardinality: int, word: str):
        """Pluralises words that just have a suffix if pluralised."""
        if cardinality - 1:
            word += "s"
        return f"{cardinality:,} {word}"

    @staticmethod
    async def convert_to_tokens(ctx, amount) -> int:
        """
        Converts an amount to a token value. If it's unable to do so it will return None.
        """
        converter = {"k": 1, "m": 1_000, "b": 1_000_000}

        try:
            amount = int(amount)
        except ValueError:
            pass

        if isinstance(amount, str) and amount[-1] in converter:
            try:
                amount = converter[amount[-1]] * int(amount[:-1])
            except ValueError:
                amount = 0
        if isinstance(amount, str) or amount <= 0:
            await ctx.send(embed=token_conversion_message(ctx))
            amount = 0
        return amount

    @staticmethod
    def tokens_check(amount) -> int:
        """
        Converts an amount to a token value. If it's unable to do so it will return None.
        """
        converter = {"k": 1, "m": 1_000, "b": 1_000_000}

        try:
            amount = int(amount)
        except ValueError:
            pass

        if isinstance(amount, str) and amount[-1] in converter:
            try:
                amount = converter[amount[-1]] * int(amount[:-1])
            except ValueError:
                amount = 0
        if isinstance(amount, str) or amount <= 0:
            amount = 0
        return amount


class GuildOnlyCog(BaseCog):
    """
    Base cog for any tag-implementation cogs. Lets me inject some basic functionality that is shared across this
    extension.
    """

    def cog_check(self, ctx):
        return ctx.guild is not None
