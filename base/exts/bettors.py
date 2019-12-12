#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import json
import random

import aiofiles
import asyncpg
import discord
from discord.ext import commands

from base.core.base_cog import BaseCog
from base.utils.embeds import Embed
from base.utils.game_utils import show_update
from base.utils.premade_messages import not_enough_message


class BettorCog(BaseCog):
    @commands.command()
    async def setseed(self, ctx, *, seed):
        if seed:
            try:
                all(ord(c) < 128 for c in seed)
            except UnicodeEncodeError:
                return await ctx.send(
                    embed=Embed(
                        title="Invalid Seed",
                        description="A seed must not have mentions and must be shorter than 20 characters",
                    ).set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
                )
            if len(seed) > 20 or ctx.message.mentions:
                return await ctx.send(
                    embed=Embed(
                        title="Invalid Seed",
                        description="A seed must not have mentions and must be shorter than 20 characters",
                    )
                ).set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
        await self.database.execute(
            self.sql_cache.read("change_seed.sql"), ctx.author.id, seed
        )
        await ctx.send(
            embed=Embed(
                title="Seed Successfully Updated",
                description=f"Your seed was successfully changed to **{seed}**",
            ).set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
        )

    @commands.command()
    async def seed(self, ctx, member: discord.Member = None):
        member = ctx.author if member is None else member
        mem_row = await self.database.fetchrow(
            self.sql_cache.read("get_member.sql"), member.id
        )
        await ctx.send(
            embed=Embed(
                title="Seed",
                description=f"The seed for {member.mention} is: {mem_row['seed'] if mem_row else 'default'}",
            ).set_author(name=member.display_name, icon_url=member.avatar_url)
        )

    @commands.command()
    async def raffles(self, ctx):
        """Checks the open raffles."""
        await ctx.send(
            embed=Embed(
                title="Open Raffles",
                description=(
                    "\n".join(
                        [
                            f"Raffle {raffle}: {self.plur_simple(self.bot.raffles[raffle]['price'], 'token')} per "
                            f"ticket, {len(self.bot.raffles[raffle]['members'])}/{self.bot.raffles[raffle]['tickets']} "
                            f"tickets sold, "
                            f"{round(self.bot.raffles[raffle]['price'] * self.bot.raffles[raffle]['tickets'] * .95)} "
                            f"tokens payout!"
                            for raffle in self.bot.raffles
                        ]
                        if self.bot.raffles
                        else ["None"]
                    )
                ),
            )
        )

    @commands.command()
    async def buyticket(self, ctx, raffle_number):
        """Buy's a ticket from a raffle."""
        if raffle_number not in self.bot.raffles:
            return await ctx.send(embed=Embed(title=f"A raffle with the number {raffle_number} could not be found!"))
        overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            ctx.author: discord.PermissionOverwrite(read_messages=True),
            ctx.guild.get_role(self.config.roles["cashier"]): discord.PermissionOverwrite(read_messages=True),
        }
        channel = await ctx.guild.create_text_channel(
            name=f"raffle-{raffle_number}",
            category=ctx.guild.get_channel(self.config.categories["game_room"]),
            overwrites=overwrites,
        )
        raffle = self.bot.raffles[raffle_number]
        await channel.send(
            f"{ctx.author.mention}, respond with the `!buy number of tickets` you would like to buy. Example:\n"
            f"```!buy 50```",
            embed=Embed(
                title="Raffle Tickets Purchase",
                description=f"Raffle {raffle_number}: {self.plur_simple(raffle['price'], 'token')} per ticket, "
                f"{raffle['tickets'] - len(raffle['members'])} tickets remain, "
                f"{round(raffle['price'] * raffle['tickets'] * .95)} tokens payout!",
            ),
        )

        def check(m):
            content = m.content.lower().split()
            return (
                len(content) == 2
                and content[0] == "!buy"
                and m.author.id == ctx.author.id
                and m.channel.id == channel.id
            )

        message = (await self.bot.wait_for("message", check=check)).content.lower().split()[1]
        try:
            amount = await self.convert_to_tokens(ctx, message)
        except TypeError:
            await channel.send("The amount couldn't be parsed.  This channel will be auto archived in 15s.")
            await asyncio.sleep(15)
            return await channel.delete(reason="Channel auto-archived")

        await channel.send(
            embed=Embed(
                title="Confirm",
                description=f"This action will remove {amount * raffle['price']} tokens from your wallet. Type "
                f"`!confirm` to confirm or `!cancel` to decline",
            )
        )

        def check(m):
            return (
                m.content.lower() in ["!confirm", "!cancel"]
                and m.author.id == ctx.author.id
                and m.channel.id == channel.id
            )

        confirm = (await self.bot.wait_for("message", check=check)).content.lower() == "!confirm"
        if not confirm:
            return await channel.delete(reason="Channel auto-archived")

        if amount > raffle["tickets"] - len(raffle["members"]):
            await channel.send(
                "This channel will be auto archived in 15s.",
                embed=Embed(description="There are not enough tickets to buy that many!"),
            )
            await asyncio.sleep(15)
            return await channel.delete(reason="Channel auto-archived")

        try:
            await self.database.execute(
                self.sql_cache.read("remove_currency.sql"), ctx.author.id, amount * raffle["price"]
            )
        except asyncpg.CheckViolationError:
            await channel.send("This channel will be auto archived in 15s.", embed=not_enough_message(ctx))
            await asyncio.sleep(15)
            return await channel.delete(reason="Channel auto-archived")

        mem_row = await self.database.fetchrow(self.sql_cache.read("get_member.sql"), ctx.author.id)
        if mem_row is None:
            await channel.send("This channel will be auto archived in 15s.", embed=not_enough_message(ctx))
            await asyncio.sleep(15)
            return await channel.delete(reason="Channel auto-archived")
        await channel.send(
            embed=Embed(description=f"{round(raffle['price'] * amount)} tokens have been removed from your balance.")
        )
        await show_update(self, ctx.author, raffle["price"] * amount, mem_row)

        role = discord.utils.get(ctx.guild.roles, name=str(raffle_number))
        await ctx.author.add_roles(role)

        for _ in range(amount):
            self.bot.raffles[raffle_number]["members"].append(ctx.author.id)

        if raffle["tickets"] <= len(raffle["members"]):
            overwrites = {
                ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                ctx.guild.get_role(self.config.roles["cashier"]): discord.PermissionOverwrite(
                    read_messages=True, send_messages=False
                ),
                role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
            }
            raffle_channel = await ctx.guild.create_text_channel(
                name=f"raffle-{raffle_number}",
                category=ctx.guild.get_channel(self.config.categories["game_room"]),
                overwrites=overwrites,
            )
            await raffle_channel.send(
                ctx.guild.default_role,
                embed=Embed(
                    description=f"The raffle for {raffle_number} for {round(raffle['price'] * raffle['tickets'] * .95)}"
                    f" will be rolled in 30 seconds!"
                ),
            )
            await asyncio.sleep(30)
            winner = ctx.guild.get_member(random.choice(raffle["members"]))
            await raffle_channel.send(
                winner.mention,
                embed=Embed(
                    title="Raffle Ended",
                    description=f"The raffle has ended and {winner.mention} has won "
                    f"{round(raffle['price'] * raffle['tickets'] * .95)}",
                ),
            )
            winner_row = await self.database.fetchrow(self.sql_cache.read("get_member.sql"), winner.id)
            await self.database.execute(
                self.sql_cache.read("add_currency.sql"), winner.id, round(raffle["price"] * raffle["tickets"] * 0.95)
            )
            await show_update(self, winner, round(raffle["price"] * raffle["tickets"] * 0.95), winner_row, True)
            self.bot.raffles.pop(str(raffle_number))
            await role.delete()

            await self.database.execute(
                self.sql_cache.read("add_currency.sql"), self.bot.user.id,
                round(raffle["price"] * raffle["tickets"] * 0.05)
            )

        async with aiofiles.open("src/raffles.json", "w") as fp:
            await fp.write(json.dumps(self.bot.raffles))

        await asyncio.sleep(90)
        await channel.delete(reason="Channel auto-archived")

    @commands.command(aliases=["w", "wallet", "bal"])
    async def balance(self, ctx, member: discord.Member = None):
        """Checks the balance of a member."""
        if not member:
            member = ctx.author
        bal = await self.database.fetchrow(self.sql_cache.read("get_member.sql"), member.id)
        embed = Embed(title=f"Tokens", description=f"{bal['tokens'] if bal else 0:,}")
        embed.set_author(name=member.display_name, icon_url=member.avatar_url)
        await ctx.send(embed=embed)

    @commands.command(aliases=["withdraw"])
    async def deposit(self, ctx):
        """Withdraw or deposit for tokens."""
        deposit_room = ctx.guild.get_channel(self.config.categories["bal_update"])
        cashier = ctx.guild.get_role(self.config.roles["cashier"])
        overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            ctx.author: discord.PermissionOverwrite(read_messages=True),
            cashier: discord.PermissionOverwrite(read_messages=True),
        }
        channel = await ctx.guild.create_text_channel(
            name=f"{ctx.author.name}-{ctx.invoked_with}", category=deposit_room, overwrites=overwrites
        )
        await channel.send(
            f"{ctx.guild.get_role(self.config.roles['cashier']).mention}, {ctx.author.mention} "
            f"would like to {ctx.invoked_with.lower()}"
        )


def setup(bot):
    bot.add_cog(BettorCog(bot))
