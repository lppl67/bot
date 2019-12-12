#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
import traceback
from datetime import timedelta

import aiofiles
import discord
from discord.ext import commands

from base.core import base_cog
from base.utils.embeds import Embed
from base.utils.utils import timedelta_str


class SudoCog(base_cog.BaseCog):
    def __init__(self, bot):
        super().__init__(bot)

        self.bot.loop.create_task(self._edit_reboot_message())

    async def _edit_reboot_message(self):
        await self.bot.wait_until_ready()

        try:
            async with aiofiles.open("src/REBOOT", "r") as fp:
                reboot_instructions = (await fp.read()).strip().split("\n")

            message = await self.bot.get_channel(int(reboot_instructions[1])).fetch_message(int(reboot_instructions[2]))

            restart_time = timedelta(seconds=time.time() - float(reboot_instructions[0]))

            await message.edit(
                embed=Embed(
                    description=f"**{self.bot.user.name}** has restarted (took {timedelta_str(restart_time)})",
                    colour=discord.Colour.green(),
                )
            )
        except (AttributeError, discord.NotFound):
            self.logger.error("Couldn't find either the channel or the message!")
        except (IndexError, FileNotFoundError):
            self.logger.error("Invalid REBOOT file!")

    @commands.command()
    @commands.is_owner()
    async def reload(self, ctx):
        """Reload all modules"""
        async with ctx.typing():
            extensions = list(ctx.bot.extensions)
            failures = {}
            successes = []
            for extension in extensions:
                try:
                    ctx.bot.reload_extension(extension)
                    successes.append(extension)
                except Exception as ex:
                    failures[extension] = ex

            pag = commands.Paginator(prefix="```diff")
            if successes:
                pag.add_line("Successful reloads:")
            for success in successes:
                pag.add_line(f"+ {success}")

            if failures:
                pag.add_line("Failures:")
            for failed_ext, reason in failures.items():
                pag.add_line(f"- {failed_ext} because {type(reason).__name__}: {reason}")

            pag.add_line("Completed reload")

        for page in pag.pages:
            await ctx.send(page)

    @commands.command(aliases=["kys", "die"])
    @commands.is_owner()
    async def restart(self, ctx):
        """
        Restarts the bot by logging out and letting the container restart.
        """
        restart_time = time.time()
        self.bot.logger.info(f"Rebooting by order from `{ctx.author}`")
        embed = Embed(description=f"**{self.bot.user.name}** is restarting...", colour=discord.Colour.gold())
        msg = await ctx.send(embed=embed)

        async with aiofiles.open("/src/REBOOT", "w") as fp:
            await fp.write(f"{restart_time}\n{ctx.channel.id}\n{msg.id}")

        await self.bot.logout()

    @commands.group()
    @commands.is_owner()
    async def db(self, ctx):
        """Run SQL or expires the connections to PostgreSQL and reacquires them"""
        pass

    @db.command()
    @commands.is_owner()
    async def expire(self, ctx):
        """Expire the connections to PostgreSQL and reacquire them"""
        async with ctx.typing():
            await self.database.expire_connections()
            async with self.database.acquire() as conn:
                await conn.fetch("SELECT 1")
        await ctx.send("Expired and created new connections")

    @db.command()
    @commands.is_owner()
    async def do(self, ctx, *, query):
        """Run SQL"""
        pag = commands.Paginator()
        pag.add_line("Results: ")

        try:
            self.logger.warning("Interactive interpreter running %s", query)
            async with self.database.acquire() as conn, ctx.typing():
                async with conn.transaction():
                    i = 1
                    async for record in conn.cursor(query):
                        if i > 10:
                            break

                        line = f"{i}: {record}"[:1000]
                        pag.add_line(line)

                        i += 1
        except Exception as ex:
            self.logger.exception("Exception running eval'ed query", exc_info=ex)
            for line in traceback.format_exc().split("\n"):
                pag.add_line(line[:1000])

        for p in pag.pages:
            await ctx.send(p)

    @commands.command()
    async def uptime(self, ctx):
        """Get my uptime"""
        await ctx.send(timedelta_str(ctx.bot.uptime))


def setup(bot):
    bot.add_cog(SudoCog(bot))
