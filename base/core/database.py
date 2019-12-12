#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Initializes our tables if they do not already exist.
"""
import asyncio
import logging

import asyncpg.exceptions

from base.utils import utils

_LOGGER = logging.getLogger(__name__)
TOTAL_WARM_UP_RETRIES = 10


class SQLCache:
    def __init__(self):
        self._cache = {}

    def read(self, file):
        if file not in self._cache:
            path = utils.relative_to_here("sql", file)
            _LOGGER.info("Reading %s", path)
            with open(path) as fp:
                self._cache[file] = fp.read()

        return self._cache[file]


async def _initialize_schema(cache, conn: asyncpg.Connection) -> None:
    """Initializes the schema and tables for this database."""
    # noinspection PyProtectedMember
    try:
        _LOGGER.info("Creating initial tables if they don't exist")
        await conn.execute(cache.read("schema.sql"))

        _LOGGER.info("Initialization completed of database container")
    except asyncpg.exceptions._base.PostgresError as ex:
        _LOGGER.critical("Could not initialize database safely", exc_info=ex)
        raise RuntimeError("Startup failed") from ex


async def create_connection_pool(cache, config):
    _LOGGER.info("Initializing asyncpg connection")

    database = None

    for i in range(TOTAL_WARM_UP_RETRIES):
        try:
            database = await asyncpg.create_pool(**config.to_dict())
        except Exception as ex:
            if isinstance(ex, (asyncpg.CannotConnectNowError, OSError)) and i + 1 < TOTAL_WARM_UP_RETRIES:
                _LOGGER.info(
                    "Database is still warming up, will wait for 5 seconds and try again (retry %s/%s)",
                    i + 1,
                    TOTAL_WARM_UP_RETRIES,
                )
            else:
                raise RuntimeError("Postgres is not available!")

            await asyncio.sleep(5)
        else:
            _LOGGER.info("Connected to postgres successfully: %s", database)
            break

    # Ensure tables are set up.
    async with database.acquire() as conn:
        await _initialize_schema(cache, conn)

    return database
