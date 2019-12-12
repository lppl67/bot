import asyncio
import random

import asyncpg
import discord

from base.utils.embeds import Embed
from base.utils.premade_messages import not_enough_message

__all__ = "send_to_history", "show_update", "game_check", "delete_room", "get_unique_number", "prov_fair_fp"


async def send_to_history(self, author, row: asyncpg.Record, dice_roll: dict):
    rolls_history = self.bot.get_channel(self.config.channels["rolls_history"])
    await rolls_history.send(
        embed=Embed(
            description=f"{author.mention} rolled **{'-'.join([str(dice) for dice in dice_roll['rolls']])}**"
        ).set_footer(text=f"Seed: {row['seed']} • Nonce: {'-'.join([str(nonce) for nonce in dice_roll['nonces']])}")
    )


async def show_update(self, author: discord.Member, amount: int, row: asyncpg.Record, add: bool = False) -> None:
    embed = Embed(title="Balance Update")
    embed.add_field(name="Previous Balance", value=f"{row['tokens'] - amount if add else row['tokens'] + amount:,}")
    embed.add_field(name=f"Tokens {'Added' if add else 'Removed'}", value=f"{amount:,}")
    embed.add_field(name="New Balance", value=f"{row['tokens']:,}")
    embed.set_author(name=author.display_name, icon_url=author.avatar_url)

    update_channel = self.bot.get_channel(self.config.channels["archive"])
    await update_channel.send(embed=embed)


async def game_check(self, ctx, amount) -> bool or (int, asyncpg.Record):
    amount = await self.convert_to_tokens(ctx, amount.lower())
    if amount <= 0:
        return -1

    try:
        await self.database.execute(self.sql_cache.read("remove_currency.sql"), ctx.author.id, amount)
    except asyncpg.CheckViolationError:
        await ctx.send(embed=not_enough_message(ctx))
        return -1

    mem_row = await self.database.fetchrow(self.sql_cache.read("get_member.sql"), ctx.author.id)
    if mem_row is None:
        await ctx.send(embed=not_enough_message(ctx))
        return -1

    return amount, mem_row


async def delete_room(self, channel):
    await asyncio.sleep(120)
    await channel.delete(reason="Game auto-archived")
    self.bot.game_numbers.remove(int(channel.name))


def get_unique_number(self):
    return random.choice(list(set(range(1_000, 9_999)) - set(self.bot.game_numbers)))


def prov_fair_fp(value: float) -> str:
    if 0.01 <= value <= 14.28:
        return "red"
    elif 14.29 <= value <= 28.57:
        return "yellow"
    elif 28.58 <= value <= 42.86:
        return "orange"
    elif 42.87 <= value <= 57.15:
        return "rainbow"
    elif 57.16 <= value <= 71.44:
        return "blue"
    elif 71.45 <= value <= 85.73:
        return "purple"
    else:
        return "pastel"
