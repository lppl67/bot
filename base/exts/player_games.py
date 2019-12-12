import asyncio
from collections import Counter

import asyncpg
import discord
from discord.ext import commands

from base.core.base_cog import BaseCog
from base.utils.embeds import Embed
from base.utils.game_utils import *
from base.utils.premade_messages import not_enough_message
from base.utils.provably_fair import roll


class PlayerCog(BaseCog):
    """Games vs other Players."""

    @commands.group()
    @commands.guild_only()
    async def open(self, ctx):
        """Starts a game of either dd or fp."""
        pass

    @open.command()
    async def dd(self, ctx, amount):
        """Roll a dice between 2-12 vs another player.  Higher roll wins 1.9x their bet."""
        try:
            amount, mem_row = await game_check(self, ctx, amount)
        except TypeError:
            return

        await show_update(self, ctx.author, amount, mem_row)
        game_num = await self._pre_game(ctx, amount)
        channel, competitor = await self._confirm_game(ctx, amount, game_num, mem_row)
        if channel is None or competitor is None:
            return

        await channel.send(
            f"Your Dice Duel game has been called by {competitor.mention}, {ctx.author.mention} rolls first"
        )

        end_game = False
        while not end_game:
            author_rolls = await self._dd_roll(mem_row, channel, ctx.author)
            competitor_row = await self.database.fetchrow(self.sql_cache.read("get_member.sql"), competitor.id)
            competitor_rolls = await self._dd_roll(competitor_row, channel, competitor)
            if sum(author_rolls["rolls"]) > sum(competitor_rolls["rolls"]):
                await self._win_message(channel, ctx.author, amount)
                end_game = True
            elif sum(author_rolls["rolls"]) < sum(competitor_rolls["rolls"]):
                await self._win_message(channel, competitor, amount)
                end_game = True
            else:
                await channel.send(embed=Embed(description="It was a tie! Playing again."))

    @open.command()
    async def fp(self, ctx, amount):
        """Plays a game of flower poker."""
        try:
            amount, mem_row = await game_check(self, ctx, amount)
        except TypeError:
            return

        await show_update(self, ctx.author, amount, mem_row)
        game_num = await self._pre_game(ctx, amount)
        channel, competitor = await self._confirm_game(ctx, amount, game_num, mem_row)
        if channel is None or competitor is None:
            return

        await channel.send(
            f"Your Flower Poker game has been called by {competitor.mention}, {ctx.author.mention} plants first"
        )

        end_game = False
        while not end_game:
            author_roll = await self._fp_roll(mem_row, channel, ctx.author)
            competitor_row = await self.database.fetchrow(self.sql_cache.read("get_member.sql"), competitor.id)
            competitor_roll = await self._fp_roll(competitor_row, channel, competitor)
            if author_roll > competitor_roll:
                await self._win_message(channel, ctx.author, amount)
                end_game = True
            elif author_roll < competitor_roll:
                await self._win_message(channel, competitor, amount)
                end_game = True
            else:
                await channel.send(embed=Embed(description="It was a tie! Playing again."))

    @commands.guild_only()
    @commands.command()
    async def games(self, ctx):
        """Shows the open pvp games."""
        games = self.bot.open_games
        if len(games) == 0:
            return await ctx.send(
                embed=Embed(description=f"Sorry {ctx.author.mention}, there are no current games open!").set_author(
                    name=ctx.author.display_name, icon_url=ctx.author.avatar_url
                )
            )

        embed = Embed(title="Current Open Games")
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
        embed.add_field(
            name="Games",
            value="\n".join(
                [
                    f"{game} - {games[game]['game']} - {games[game]['amount']:,} - {games[game]['author'].mention}"
                    for game in games
                ]
            ),
        )
        await ctx.send(embed=embed)

    async def _pre_game(self, ctx, amount) -> int:
        game_number = get_unique_number(self)

        self.bot.open_games[game_number] = {"author": ctx.author, "amount": amount, "game": ctx.invoked_with.upper()}
        self.bot.game_numbers.add(game_number)
        game = "Flower Poker" if ctx.invoked_with.lower() == "fp" else "Dice Duels"

        await ctx.send(
            embed=Embed(description=f"Your {game} game was successfully created with ID: **{game_number}**").set_author(
                name=ctx.author.display_name, icon_url=ctx.author.avatar_url
            )
        )

        return game_number

    async def _confirm_game(
        self, ctx, amount: int, game_number: int, mem_row: asyncpg.Record
    ) -> (discord.TextChannel, discord.Member):
        def check(m):
            content = m.content.lower().split()
            return (
                len(content) == 2
                and content[1] == str(game_number)
                and (
                    (content[0] == "!call" and (m.author.id != ctx.author.id))
                    or (
                        (m.author.id == ctx.author.id or m.author.guild_permissions.administrator)
                        and content[0] == "!cancel"
                    )
                )
            )

        while True:
            msg = await self.bot.wait_for("message", check=check)

            if msg.content.lower().split()[0] == "!cancel":
                await self.database.execute(self.sql_cache.read("add_currency.sql"), ctx.author.id, amount)
                await ctx.send(
                    embed=Embed(
                        description=f"Game **{game_number}** was successfully cancelled by {msg.author.mention}\n"
                        f"{self.plur_simple(amount, 'token')} was refunded to {ctx.author.mention}"
                    ).set_author(name=msg.author.display_name, icon_url=msg.author.avatar_url)
                )
                await show_update(self, ctx.author, amount, mem_row, True)
                self._remove_game(game_number)
                return None, None
            try:
                await self.database.execute(self.sql_cache.read("remove_currency.sql"), msg.author.id, amount)
                msg_row = await self.database.fetchrow(self.sql_cache.read("get_member.sql"), msg.author.id)
                await show_update(self, msg.author, amount, msg_row)
                self._remove_game(game_number)
                return await self._create_game_room(ctx, game_number, msg.author), msg.author
            except asyncpg.CheckViolationError:
                await ctx.send(embed=not_enough_message(ctx))

    async def _create_game_room(self, ctx, game_number: int, competitor: discord.Member) -> discord.TextChannel:
        game_room = self.bot.get_channel(self.config.categories["game_room"])

        host = ctx.guild.get_role(self.config.roles["host"])

        return await ctx.guild.create_text_channel(
            name=game_number,
            category=game_room,
            overwrites={
                ctx.author: discord.PermissionOverwrite(send_messages=True),
                host: discord.PermissionOverwrite(send_messages=True),
                ctx.guild.default_role: discord.PermissionOverwrite(send_messages=False),
                competitor: discord.PermissionOverwrite(send_messages=True),
            },
        )

    def _remove_game(self, game_number: int):
        self.bot.open_games.pop(game_number)
        self.bot.game_numbers.remove(game_number)

    @staticmethod
    def _calc_flower_value(flowers: list) -> (int, str):
        flowers = Counter(flowers).most_common()

        if flowers[0][1] == 1:
            return 0, "bust"
        elif flowers[0][1] == 2:
            return (1, "1 pair") if flowers[1][1] == 1 else (2, "2 pairs")
        elif flowers[0][1] == 3:
            return (3, "3 of a kind") if flowers[1][1] == 1 else (4, "full house")
        elif flowers[0][1] == 4:
            return 5, "4 of a kind"
        elif flowers[0][1] == 5:
            return 6, "5 of a kind"

    async def _dd_roll(self, mem_row: asyncpg.Record, channel: discord.TextChannel, author: discord.Member) -> dict:
        await channel.send(
            embed=Embed(
                description="Please type **!roll** when ready, or the bot will auto-roll in 30 seconds!"
            ).set_author(name=author.name, icon_url=author.avatar_url),
        )
        try:
            await self.bot.wait_for(
                "message",
                check=lambda m: m.author.id == author.id and m.content == "!roll" and m.channel.id == channel.id,
                timeout=30,
            )
        except asyncio.TimeoutError:
            pass
        rolls = roll(self, mem_row["seed"], 2, True)
        embed = self._send_multiple_embed(mem_row, author, rolls)
        await self.bot.get_channel(self.config.channels["rolls_history"]).send(embed=embed)
        await channel.send(embed=embed)
        return rolls

    async def _fp_roll(self, row: asyncpg.Record, channel: discord.TextChannel, author: discord.Member) -> int:
        await channel.send(
            f"{author.mention}",
            embed=Embed(
                description="Please type **!plant** when ready, or the bot will auto-plant in 30 seconds!"
            ).set_author(name=author.name, icon_url=author.avatar_url),
        )
        try:
            await self.bot.wait_for(
                "message",
                check=lambda m: m.author.id == author.id and m.content == "!plant" and m.channel.id == channel.id,
                timeout=30,
            )
        except asyncio.TimeoutError:
            pass
        rolls = roll(self, row["seed"], 5)
        flowers = [prov_fair_fp(author_roll) for author_roll in rolls["rolls"]]
        values = self._calc_flower_value(flowers)
        embed = Embed(title="Flower Poker")
        embed.add_field(
            name=author.display_name,
            value=f"{''.join([self.config.flowers[flower].emoji for flower in flowers])}\n{values[1]}",
        )
        embed.set_footer(text=f"Seed: {row['seed']} • Rolls: {rolls['rolls']} " f"• Nonces: {rolls['nonces']}")
        embed.set_author(name=author.display_name, icon_url=author.avatar_url)
        await channel.send(embed=embed)
        await self.bot.get_channel(self.config.channels["rolls_history"]).send(embed=embed)
        return values[0]

    @staticmethod
    def _send_multiple_embed(row: asyncpg.Record, author: discord.Member, dice_rolls: dict) -> discord.Embed:
        return (
            Embed(description=f"{author.mention} rolled a sum of **{sum(dice_rolls['rolls'])}** with 2 six-sided die.")
            .set_footer(text=f"Seed: {row['seed']} • Rolls: {dice_rolls['rolls']} " f"• Nonces: {dice_rolls['nonces']}")
            .set_author(name=author.display_name, icon_url=author.avatar_url)
        )

    async def _win_message(self, channel: discord.TextChannel, winner: discord.Member, amount: int):
        amount = round(amount * 1.9)
        await self.database.execute(self.sql_cache.read("add_currency.sql"), winner.id, amount)
        winner_row = await self.database.fetchrow(self.sql_cache.read("get_member.sql"), winner.id)
        await show_update(self, winner, amount, winner_row, True)
        await self.database.execute(self.sql_cache.read("add_currency.sql"), self.bot.user.id, round(amount * 0.05))
        await channel.send(embed=Embed(description=f"{winner.mention} has won **{self.plur_simple(amount, 'token')}**"))


def setup(bot):
    bot.add_cog(PlayerCog(bot))
