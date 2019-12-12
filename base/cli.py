#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import logging
import os

import yaml

from .core import config, client


async def async_main(configuration) -> None:
    bot = client.Client(configuration=configuration)

    try:
        await bot.start()
    finally:
        await bot.close()


def main():
    config_path = os.getenv("PYGEAR_CONFIG_FILE", "../config.yaml")

    with open(config_path) as fp:
        configuration = config.Config.from_dict(yaml.safe_load(fp))

    logging.basicConfig(
        level=configuration.logging.level,
        format="%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Mute aiohttp server for health checking
    logging.getLogger("aiohttp.access").setLevel(logging.ERROR)

    try:
        import uvloop

        logging.info("Using uvloop for asyncio event loop native implementation")
        uvloop.install()
    except ImportError:
        logging.info("Not using uvloop for asyncio event loop native implementation")

    asyncio.run(async_main(configuration))
