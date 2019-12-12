#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import datetime
import logging
import time
import traceback
import typing

import asyncpg
from discord.ext import commands

import base
from base.utils.provably_fair import update_seed
from . import config, database


class Client(commands.Bot):
    """
    Based off of commands.Bot, with a built in connection pool, amongst other things.
    """

    def __init__(self, configuration=config.Config) -> None:
        self.server_seed_hash = str
        self.server_seed = str
        self.nonce = int
        self.open_games = dict()
        self.game_numbers = set()
        self.raffles = dict()

        self.started_at = float("nan")
        self.logger = logging.getLogger(__name__)
        self.config = configuration
        self.database: typing.Optional[asyncpg.pool.Pool] = None
        self.sql_cache = database.SQLCache()
        self.command_invoke_count = 0
        super().__init__(command_prefix=self.config.bot.command_prefix)

    @property
    def uptime(self) -> datetime:
        return datetime.timedelta(seconds=time.perf_counter() - self.started_at)

    async def start(self) -> None:
        self.database = await database.create_connection_pool(self.sql_cache, self.config.postgres)
        self._load_all_extensions()
        self.logger.info("Proceeding with startup of bot")

        self.started_at = time.perf_counter()
        self.loop.create_task(update_seed(self))
        await self._start()

    async def _start(self) -> None:
        await super().start(self.config.bot.token)

    async def close(self) -> None:
        self.logger.info("Closing asyncpg connection")
        try:
            if self.database is not None:
                await self.database.close()
        finally:
            await super().close()

    def _load_all_extensions(self):
        self.logger.info("Loading extensions...")
        extensions = set(base.extensions) - set(self.config.bot.blacklist_extensions)

        for ext in extensions:
            try:
                self.load_extension("base.exts." + ext, False)
            except Exception as ex:
                self.logger.warning("Failed to load %s because of exception", ext, exc_info=ex)
            else:
                self.logger.info("Loaded extension %s successfully", ext)

    def load_extension(self, name, mute=True):
        # Annoyingly, Dpy calls load_extension meaning we cant attach a logger to it directly or we get
        # two log entries...
        if not mute:
            self.logger.info("Loading %s", name)
        super().load_extension(name)

    def unload_extension(self, name):
        self.logger.info("Unloading %s", name)
        super().unload_extension(name)

    def reload_extension(self, name):
        self.logger.info("Reloading %s", name)
        super().reload_extension(name)

    async def on_connect(self):
        await self.get_owner()

    async def on_command_error(self, ctx, ex):
        if isinstance(ex, commands.CommandOnCooldown):
            self.logger.debug("%s is on cool down for %ss", ctx.author, ex.retry_after)
            await ctx.message.add_reaction("\N{SNOWFLAKE}")
            await asyncio.sleep(ex.retry_after)
            await ctx.message.remove_reaction("\N{SNOWFLAKE}", self.user)
        else:
            self.logger.error("".join(traceback.format_exception(type(ex), ex, ex.__traceback__, 4)))

    async def on_command(self, ctx):
        self.command_invoke_count += 1

    async def get_owner(self):
        if self.owner_id is None:
            info = await self.application_info()
            self.owner_id = info.owner.id
        return self.owner_id
