# !/usr/bin/env python3
# -*- coding: utf-8 -*-
import textwrap

import discord
from discord.ext import commands

from base.utils import navigator

INDEX_MAX_PAGE_ITEMS = 6


class HelpCog(commands.Cog):
    def __init__(self, bot):
        self._bot = bot
        self._old_help = bot.get_command("help")
        bot.remove_command("help")

    def cog_unload(self):
        self._bot.add_command(self._old_help)

    # Use emptystring as the default instead of None, as
    # get_command will TypeError with a NoneType passed
    # as a parameter.
    @commands.command(name="help")
    async def help_command(self, ctx, *, query=""):
        """Shows this message"""
        command = ctx.bot.get_command(query)
        if command is None:
            await self.send_index(ctx)
        else:
            await self.send_page(ctx, command)

    async def send_index(self, ctx):
        index_pages = []
        async for page in self.make_index_embeds(ctx):
            index_pages.append(page)

        navigator.Navigator.from_context(ctx, index_pages).run()

    async def send_page(self, ctx, command):
        await ctx.send(embed=self.make_command_page_embed(ctx, command))

    @staticmethod
    def embed(ctx, **kwargs):
        embed = discord.Embed(color=0xB3F9FF, **kwargs)
        embed.set_author(name=ctx.bot.user.name, icon_url=ctx.bot.user.avatar_url)
        return embed

    async def make_index_embeds(self, ctx):
        description = []
        for command in sorted(set(ctx.bot.all_commands.values()), key=lambda c: c.qualified_name):
            try:
                if not await command.can_run(ctx):
                    continue
            except:
                continue

            description.append(f"• **{command.qualified_name}** - {command.short_doc}")

        for i in range(0, len(description), INDEX_MAX_PAGE_ITEMS):
            slice = description[i : i + INDEX_MAX_PAGE_ITEMS]
            if slice:
                yield self.embed(ctx, title=f"Help", description="\n".join(slice))

    def make_command_page_embed(self, ctx, command):
        e = self.embed(
            ctx,
            title=command.qualified_name,
            description=textwrap.dedent(
                f"""
                `{command.qualified_name} {command.signature}`

                {command.help or ""}
            """
            ),
        )

        if command.aliases:
            e.add_field(name="Aliases", value=", ".join(command.aliases))

        return e


def setup(bot):
    bot.add_cog(HelpCog(bot))
