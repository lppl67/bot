#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import math
import secrets

import aiofiles
import discord

from base.utils.embeds import Embed

__all__ = ("roll_dice", "update_seed", "roll")

import hashlib
import hmac


async def update_seed(bot):
    await bot.wait_until_ready()

    try:
        async with aiofiles.open("SEEDS") as fp:
            bot.server_seed, bot.server_seed_hash = (await fp.read()).strip().split("\n")

    except (AttributeError, discord.NotFound, IndexError, FileNotFoundError):
        bot.logger.error("No SEED file found... Generating a new seed!")

    seeds = discord.utils.get(bot.get_all_channels(), name="seeds")

    while not bot.is_closed():
        old_hash = bot.server_seed_hash
        old_server_seed = bot.server_seed
        bot.server_seed = secrets.token_hex(32)
        bot.server_seed_hash = str(hashlib.sha256(str(bot.server_seed).encode("utf-8")).hexdigest())
        bot.nonce = 0

        embed = Embed(
            title="Provably Fair",
            description=f"**Previous Hash:** {old_hash}\n"
            f"**Previous Seed:** {old_server_seed}\n"
            f"**Current Hash:** {bot.server_seed_hash}",
        )
        await seeds.send(embed=embed)

        async with aiofiles.open("SEEDS", "w") as fp:
            await fp.write(f"{bot.server_seed}\n{bot.server_seed_hash}")

        await asyncio.sleep(12 * 60 * 60)


def roll(self, seed, rolls: int = 1, out_of_six: bool = False) -> dict:
    results = {"rolls": [], "nonces": []}
    for _ in range(rolls):
        if out_of_six:
            results["rolls"].append(math.ceil(roll_dice(self.bot.server_seed, f"{seed}-{self.bot.nonce}") / (100 / 6)))
        else:
            results["rolls"].append(roll_dice(self.bot.server_seed, f"{seed}-{self.bot.nonce}"))
        results["nonces"].append(self.bot.nonce)
        self.bot.nonce += 1
    return results


def roll_dice(server_seed, client_seed):
    index = 0
    hasher = hmac.new(bytes(str(server_seed), "ascii"), bytes(str(client_seed), "ascii"), hashlib.sha512).hexdigest()
    lucky = int(hasher[index * 5 : index * 5 + 5], 16)
    while lucky >= 999_999:
        index += 1
        lucky = int(hasher[index * 5 : index * 5 + 5], 16)
        if index * 5 + 5 > 128:
            lucky = 99.99
            break
    lucky %= 10_000
    lucky /= 100
    return round(lucky + 0.01, 2)
