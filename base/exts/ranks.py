#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import discord
from discord.ext import commands

from base.core.base_cog import BaseCog


def is_cashier(ctx):
    return discord.utils.get(ctx.author.roles, id=ctx.bot.config.roles["cashier"])


def is_rank(ctx):
    return discord.utils.get(ctx.author.roles, id=ctx.bot.config.roles["host"]) or is_cashier(ctx)


class RanksCog(BaseCog):
    @commands.has_role("Admin")
    @commands.guild_only()
    @commands.command(aliases=["archive"])
    async def close(self, ctx):
        """Closes and archives the channel."""
        if ctx.channel.category_id in [
            self.bot.config.categories["bal_update"],
            self.bot.config.categories["game_room"],
        ]:
            await ctx.channel.delete(reason=f"Deleted by {ctx.author}")

    @commands.check(is_cashier)
    @commands.guild_only()
    @commands.command(aliases=["remove"])
    async def add(self, ctx, member: discord.Member, amount):
        """Adds/Removes to a user's wallet"""
        amount = await self.convert_to_tokens(ctx, amount.lower())
        update_channel = ctx.guild.get_channel(self.config.channels["archive"])
        was_added = ctx.invoked_with.lower() == "add"
        if amount <= 0:
            return
        if was_added:
            await self.database.execute(self.sql_cache.read("add_currency.sql"), member.id, amount)
        else:
            await self.database.execute(self.sql_cache.read("remove_currency.sql"), member.id, amount)
        embed = discord.Embed(
            title="Update Success",
            description=f"{self.plur_simple(amount, 'token')} {'was' if amount == 1 else 'were'} successfully "
            f"{'added to' if was_added else 'removed from'} {member.mention}'s wallet.",
            color=0x0000FF,
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
        await ctx.send(embed=embed)
        await update_channel.send(embed=embed)


def setup(bot):
    bot.add_cog(RanksCog(bot))
