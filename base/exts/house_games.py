import asyncio
from collections import Counter

import asyncpg
import discord
from asyncpg import CheckViolationError
from discord.ext import commands

from base.core.base_cog import BaseCog
from base.utils.embeds import Embed
from base.utils.game_utils import *
from base.utils.provably_fair import roll


class HouseCog(BaseCog):
    """Games vs the House"""

    @commands.guild_only()
    @commands.command()
    async def hc(self, ctx, amount):
        """Try to guess the the next flowers color, or whether it will be hot/cold."""
        try:
            amount, mem_row = await game_check(self, ctx, amount)
        except TypeError:
            return

        (hosts, channel), choice = await self._special_init_game(
            ctx, amount, mem_row, ["hot", "cold", "yellow", "orange", "red", "blue", "pastel", "purple", "rainbow"]
        )

        await channel.send(
            f"{ctx.author.mention}",
            embed=Embed(
                description="Please type **!plant** when ready, or the bot will auto-plant in 30 seconds!"
            ).set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url),
        )
        try:
            await self.bot.wait_for(
                "message",
                check=lambda m: m.author.id == ctx.author.id
                and m.content.lower() == "!plant"
                and m.channel.id == channel.id,
                timeout=30,
            )
        except asyncio.TimeoutError:
            pass

        await self._flower_results(ctx, channel, mem_row, amount, choice, hosts)
        await delete_room(self, channel)

    @commands.guild_only()
    @commands.command()
    async def ou(self, ctx, amount):
        """Guess whether the next rolls will be over, under, or 7."""
        try:
            amount, mem_row = await game_check(self, ctx, amount)
        except TypeError:
            return

        (hosts, channel), choice = await self._special_init_game(ctx, amount, mem_row, ["over", "under", "7"])
        await self._ready_check(ctx, channel)

        dice_roll = roll(self, mem_row["seed"], 2, True)
        win = (
            (sum(dice_roll["rolls"]) > 7 and choice == "over")
            or (sum(dice_roll["rolls"]) < 7 and choice == "under")
            or (sum(dice_roll["rolls"]) == 7 and choice == "7")
        )

        if choice == "7" and win:
            await self._payout(ctx, ctx.author if win else hosts, round(amount * 2.5) if win else 0)
        else:
            if choice == "7":
                hosts.update((host, bet * 2.5) for host, bet in hosts.items())
            await self._payout(ctx, ctx.author if win else hosts, amount if win else 0)

        if choice == "7" and win:
            embed = Embed(
                title="Over/Under",
                description=f"{ctx.author.mention} rolled a {sum(dice_roll['rolls'])} and " f"won {amount * 5} tokens",
                color=0x00FF00,
            )
        else:
            embed = Embed(
                title="Over/Under",
                description=f"{ctx.author.mention} rolled a {sum(dice_roll['rolls'])} and "
                f"{'won' if win else 'lost'} {self.plur_simple(amount * 2 if win else amount, 'token')}",
                color=0x00FF00 if win else 0xFF0000,
            )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
        embed.set_footer(
            text=f"Seed: {mem_row['seed']} • "
            f"Rolls: {'-'.join([str(rolls) for rolls in dice_roll['rolls']])} "
            f"• Nonces: {'-'.join(str(nonce) for nonce in dice_roll['nonces'])}"
        )
        await channel.send(embed=embed)

        await send_to_history(self, ctx.author, mem_row, dice_roll)
        await delete_room(self, channel)

    @commands.command()
    async def fp(self, ctx, amount):
        """Plays a game of flower poker."""
        try:
            amount, mem_row = await game_check(self, ctx, amount)
        except TypeError:
            return

        await show_update(self, ctx.author, amount, mem_row)
        hosts, channel = await self._init_game(ctx, amount, mem_row, 0.2)

        win = None
        while win is None:
            author_roll = await self._fp_roll(mem_row, channel, ctx.author)
            competitor_roll = await self._fp_roll(mem_row, channel, ctx.author, True)
            if author_roll > competitor_roll:
                await channel.send(
                    embed=Embed(
                        description=f"{ctx.author.mention} has won **{self.plur_simple(round(amount * 1.8), 'token')}**",
                        color=0x00FF00
                    )
                )
                await self._payout(ctx, ctx.author, amount, commission=0.1)
                win = True
            elif author_roll < competitor_roll:
                await channel.send(
                    embed=Embed(description=f"The house has won **{self.plur_simple(round(amount * 1.8), 'token')}**",
                                color=0xFF0000)
                )
                await self._payout(ctx, hosts, commission=0.1)
                win = False
            else:
                await channel.send(embed=Embed(description="It was a tie! Playing again."))
        await delete_room(self, channel)

    @commands.guild_only()
    @commands.command()
    async def dd(self, ctx, amount):
        """Roll a dice between 2-12 vs the house.  Higher roll wins 1.8x their bet."""
        try:
            amount, mem_row = await game_check(self, ctx, amount)
        except TypeError:
            return

        hosts, channel = await self._init_game(ctx, amount, mem_row, 0.2)
        await self._ready_check(ctx, channel)

        win = None
        while win is None:
            author_rolls = roll(self, mem_row, 2, True)
            await send_to_history(self, ctx.author, mem_row, author_rolls)

            embed = Embed(
                title="Dice Duels",
                description=f"{ctx.author.mention} rolled a {sum(author_rolls['rolls'])}\nThe host's roll will "
                f"auto-roll in 10 seconds",
            )
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
            embed.set_footer(
                text=f"Seed: {mem_row['seed']} • "
                f"Rolls: {'-'.join([str(rolls) for rolls in author_rolls['rolls']])} "
                f"• Nonces: {'-'.join(str(nonce) for nonce in author_rolls['nonces'])}"
            )
            await channel.send(embed=embed)

            await asyncio.sleep(10)

            host_rolls = roll(self, mem_row, 2, True)
            await send_to_history(self, ctx.author, mem_row, host_rolls)
            embed = Embed(title="Dice Duels", description=f"The house rolled a {sum(host_rolls['rolls'])}")
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
            embed.set_footer(
                text=f"Seed: {mem_row['seed']} • "
                f"Rolls: {'-'.join([str(rolls) for rolls in host_rolls['rolls']])} "
                f"• Nonces: {'-'.join(str(nonce) for nonce in host_rolls['nonces'])}"
            )
            await channel.send(embed=embed)
            if sum(author_rolls["rolls"]) > sum(host_rolls["rolls"]):
                win = True
            elif sum(author_rolls["rolls"]) < sum(host_rolls["rolls"]):
                win = False
            else:
                await channel.send(embed=Embed(description="It was a tie! Re-rolling for bettor in 10 seconds..."))

        await self._payout(ctx, ctx.author if win else hosts, amount if win else 0, commission=0.1)
        await channel.send(
            embed=Embed(
                title="Dice Duels",
                description=f"{ctx.author.mention} {'won' if win else 'lost'} "
                f"{self.plur_simple(amount * 1.8 if win else amount, 'token')}",
                color=0x00FF00 if win else 0xFF0000,
            )
        )

        await delete_room(self, channel)

    @commands.guild_only()
    @commands.command()
    async def bj(self, ctx, amount):
        """Try to roll higher than the dealer. You can hit to add an additional roll."""
        try:
            amount, mem_row = await game_check(self, ctx, amount)
        except TypeError:
            return

        hosts, channel = await self._init_game(ctx, amount, mem_row)
        await self._ready_check(ctx, channel)

        rolls = {"rolls": [], "nonces": []}
        self._append_roll(mem_row, rolls)
        keep_playing = True

        await self.blackjack_message(ctx, channel, mem_row, rolls)

        # while player didn't stand or bust
        while keep_playing and sum(rolls["rolls"]) < 100:
            message = await self.bot.wait_for(
                "message",
                check=lambda m: m.author.id == ctx.author.id
                and m.channel.id == channel.id
                and m.content.lower() in ["!hit", "!stand"],
            )

            if message.content.lower() == "!stand":
                keep_playing = False
                continue

            # have to do this in case they change seed mid game
            mem_row = await self.database.fetchrow(self.sql_cache.read("get_member.sql"), ctx.author.id)
            self._append_roll(mem_row, rolls)
            await self.blackjack_message(ctx, channel, mem_row, rolls)

        if sum(rolls["rolls"]) > 100:
            await channel.send(
                embed=Embed(
                    title="You Busted!",
                    description=f"You lost **{self.plur_simple(amount, 'token')}** with a "
                    f"total of **{round(sum(rolls['rolls']), 2)}**",
                    color=0xFF0000,
                ).set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
            )
            await self._payout(ctx, hosts)
        else:
            bot_rolls = {"rolls": [], "nonces": []}
            self._append_roll(mem_row, bot_rolls)
            await self.blackjack_message(ctx, channel, mem_row, bot_rolls, True)
            win = False
            # while the bot has less than the user AND they didn't bust
            while sum(bot_rolls["rolls"]) < sum(rolls["rolls"]) and sum(bot_rolls["rolls"]) < 100:
                await asyncio.sleep(1)
                self._append_roll(mem_row, bot_rolls)
                await self.blackjack_message(ctx, channel, mem_row, bot_rolls, True)

            # if the bot busted or has more than the user
            if sum(bot_rolls["rolls"]) < sum(rolls["rolls"]) or sum(bot_rolls["rolls"]) > 100:
                win = True

            await channel.send(
                embed=Embed(
                    description=f"The house rolled a total of **{round(sum(bot_rolls['rolls']), 2)}**\n"
                    f"{ctx.author.mention} rolled a total of **{round(sum(rolls['rolls']), 2)}**\n\n"
                    f"You {'won' if win else 'lost'} "
                    f"{self.plur_simple(amount * 2, 'token') if win else self.plur_simple(amount, 'token')}",
                    color=0x00FF00 if win else 0xFF0000,
                ).set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
            )
            await self._payout(ctx, ctx.author if win else hosts, amount if win else 0)

        await delete_room(self, channel)

    @commands.guild_only()
    @commands.command(name="54x2", aliases=["54"])
    async def dice(self, ctx, amount):
        """Roll higher than a 54 to win 2x your bet."""
        try:
            amount, mem_row = await game_check(self, ctx, amount)
        except TypeError:
            return

        hosts, channel = await self._init_game(ctx, amount, mem_row)
        await self._ready_check(ctx, channel)

        dice_roll = roll(self, mem_row["seed"])
        win = dice_roll["rolls"][0] >= 54

        await self._payout(ctx, ctx.author if win else hosts, amount if win else 0)

        embed = Embed(
            title="54x2 Dicing",
            description=f"{ctx.author.mention} rolled a {dice_roll['rolls'][0]} and "
            f"{'won' if win else 'lost'} {self.plur_simple(amount * 2 if win else amount, 'token')}",
            color=0x00FF00 if win else 0xFF0000,
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
        embed.set_footer(text=f"Seed: {mem_row['seed']} • Nonce: {dice_roll['nonces'][0]}")
        await channel.send(embed=embed)

        await send_to_history(self, ctx.author, mem_row, dice_roll)

        await delete_room(self, channel)

    async def _get_calls(
        self, channel, amount, special: bool = False, commission: float = None
    ) -> (dict, discord.TextChannel):
        users = dict()
        timed_out = False

        def check(m):
            content = m.content.split()
            if len(content) != 2:
                return False
            return (
                discord.utils.get(m.author.roles, id=self.config.roles["host"])
                and content[0].lower() == "!call"
                and m.channel == channel
                and self.tokens_check(content[1].lower())
            )

        while amount > 0 and not timed_out:
            try:
                message = await self.bot.wait_for("message", check=check, timeout=120)
            except asyncio.TimeoutError:
                timed_out = True
                continue

            called_amount = self.tokens_check(message.content.split()[1].lower())
            new_amount = amount - called_amount

            max_role = discord.utils.find(lambda r: r.id in self.config.maxes, message.author.roles)
            if max_role is None:
                continue
            if (
                new_amount < 0
                or self.config.maxes[max_role.id] < (called_amount * 4 if special else called_amount)
                or (
                    message.author.id in users
                    and (
                        (users[message.author.id] * 4 if special else users[message.author.id])
                        + (called_amount * 4 if special else called_amount)
                    )
                    > self.config.maxes[max_role.id]
                )
            ):
                embed = Embed(description=f"{message.author.mention}, you can't call that much!", color=0xFF0000)
                embed.set_author(name=message.author.display_name, icon_url=message.author.avatar_url)
                await channel.send(embed=embed)
                continue

            try:
                if commission is not None:
                    await self.database.execute(
                        self.sql_cache.read("remove_currency.sql"),
                        message.author.id,
                        round(called_amount * (1 - commission * 2)),
                    )
                else:
                    await self.database.execute(
                        self.sql_cache.read("remove_currency.sql"),
                        message.author.id,
                        called_amount * 4 if special else called_amount,
                    )
            except CheckViolationError:
                continue

            amount = new_amount

            if message.author.id in users.keys():
                users[message.author.id] += called_amount
            else:
                users[message.author.id] = called_amount

            await channel.send(
                embed=Embed(
                    description=f"{message.author.mention} called **{self.plur_simple(called_amount, 'token')}**.\n"
                    f"**{self.plur_simple(amount, 'token')}** remain uncalled."
                )
            )

            host_row = await self.database.fetchrow(self.sql_cache.read("get_member.sql"), message.author.id)
            if commission:
                await show_update(self, message.author, round(called_amount * (1 - commission)), host_row)
            else:
                await show_update(self, message.author, called_amount * 4 if special else called_amount, host_row)

        if amount > 0:
            users[self.bot.user.id] = amount
            await self.database.execute(self.sql_cache.read("remove_currency.sql"), self.bot.user.id, amount)

        return users, channel

    async def _ready_check(self, ctx, channel: discord.TextChannel):
        await channel.send(
            f"{ctx.author.mention}", embed=Embed(title=f"Your game is ready to be played, please type **!roll**")
        )

        await self.bot.wait_for(
            "message",
            check=lambda m: m.author.id == ctx.author.id
            and m.channel.id == channel.id
            and m.content.lower() == "!roll",
        )

    async def _payout(self, ctx, winner, amount=0, commission: float = None):
        if type(winner) == discord.Member:
            if commission is not None:
                amount *= 1 - commission
            await self.database.execute(self.sql_cache.read("add_currency.sql"), ctx.author.id, round(amount * 2))
            row = await self.database.fetchrow(self.sql_cache.read("get_member.sql"), ctx.author.id)
            await show_update(self, ctx.author, amount * 2, row, True)
        else:
            for host in winner:
                if commission is not None:
                    winner[host] *= 1 - commission
                await self.database.execute(self.sql_cache.read("add_currency.sql"), host, winner[host] * 2)
                host_row = await self.database.fetchrow(self.sql_cache.read("get_member.sql"), host)
                await show_update(self, ctx.guild.get_member(host), int(winner[host] * 2), host_row, True)

    def _append_roll(self, row: asyncpg.Record, rolls: dict):
        dice_roll = roll(self, row["seed"])
        rolls["rolls"].append(dice_roll["rolls"][0])
        rolls["nonces"].append(dice_roll["nonces"][0])

    async def _flower_results(
        self, ctx, channel: discord.TextChannel, mem_row: asyncpg.Record, amount: int, choice, hosts: dict
    ):
        dice_roll = roll(self, mem_row["seed"])
        await send_to_history(self, ctx.author, mem_row, dice_roll)

        async def _payout_message(multiplier: int, win=True):
            await channel.send(
                embed=Embed(
                    description=f"You guessed **{choice}** and picked **{flower_roll}** with a roll of "
                    f"**{dice_roll['rolls'][-1]}**\nYou **{'won' if win else 'lost'} "
                    f"{self.plur_simple(amount * multiplier, 'token')}**",
                    color=0x00FF00 if win else 0xFF0000
                )
                .set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
                .set_footer(text=f"Seed: {mem_row['seed']} • Nonce: {dice_roll['nonces'][-1]}")
                .set_thumbnail(url=self.bot.config.flowers[flower_roll].url)
            )
            await self._payout(ctx, ctx.author if win else hosts, amount * multiplier / 2 if win else amount)

        flower_roll = prov_fair_fp(dice_roll["rolls"][0])
        flower = self.config.flowers[flower_roll]
        if choice == flower.value:
            await _payout_message(2)
        elif choice == flower_roll:
            await _payout_message(5)
        else:
            if choice not in ["hot", "cold"]:
                hosts.update((host, bet * 2.5) for host, bet in hosts.items())
            await _payout_message(1, False)

    async def blackjack_message(
        self, ctx, channel: discord.TextChannel, mem_row: asyncpg.Record, rolls: dict, house=False
    ):
        embed = Embed(
            title="Blackjack",
            description=f"{'the house' if house else ctx.author.mention} rolled **{rolls['rolls'][-1]}** for "
            f"a total of **{round(sum(rolls['rolls']), 2)}.**"
            f"{'' if house else ' Type **!hit** to hit or **!stand** to stand.'}",
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
        embed.set_footer(text=f"Seed: {mem_row['seed']} • Nonce: {rolls['nonces'][-1]}")
        await channel.send(embed=embed)
        await send_to_history(self, ctx.author, mem_row, rolls)

    async def _special_init_game(
        self, ctx, amount: int, row: asyncpg.Record, calls: list
    ) -> (dict, discord.TextChannel, str):
        channel = await self._create_game_room(ctx)
        await show_update(self, ctx.author, amount, row)
        formatted_calls = "\n!".join(calls)

        embed = Embed(
            title="Make a call",
            description=f"Please respond with one of the following: \n```!{formatted_calls}```\n\nNote that "
            f"picking {'7' if '7' in calls else 'a specific flower colour'} pays out 5x while the other "
            f"options pay out 2x",
        ).set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
        await channel.send(ctx.author.mention, embed=embed)

        def check(m) -> bool:
            return (
                m.author.id == ctx.author.id
                and m.channel.id == channel.id
                and m.content.lower()[0] == "!"
                and m.content.lower()[1:] in calls
            )

        choice = (await self.bot.wait_for("message", check=check)).content.lower()[1:]

        if ctx.invoked_with.lower() == "ou":
            game = "Over/Under"
        elif ctx.invoked_with.lower() in ["54", "54x2"]:
            game = "54x2"
        elif ctx.invoked_with.lower() == "bj":
            game = "Blackjack"
        elif ctx.invoked_with.lower() == "hc":
            game = "Hot/Cold"
        elif ctx.invoked_with.lower() == "dd":
            game = "Dice Duels"
        else:
            game = "Flower Poker"

        embed = Embed(
            title=game, description=f"**{self.plur_simple(amount, 'token')}** have been removed from your balance.",
        ).set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
        await channel.send(
            f"{ctx.guild.get_role(self.bot.config.roles['host']).mention}, {ctx.author.mention} would like to play "
            f"**{game}** for **{self.plur_simple(amount, 'token')}** on **{choice}**",
            embed=embed,
        )

        return (
            await self._get_calls(
                channel, amount, choice in ["7", "rainbow", "yellow", "orange", "red", "blue", "pastel", "purple"]
            ),
            choice,
        )

    async def _init_game(
        self, ctx, amount: int, row: asyncpg.Record, commission: float = None
    ) -> (dict, discord.TextChannel):
        channel = await self._create_game_room(ctx)
        await show_update(self, ctx.author, amount, row)

        if ctx.invoked_with.lower() == "ou":
            game = "Over/Under"
        elif ctx.invoked_with.lower() in ["54", "54x2"]:
            game = "54x2"
        elif ctx.invoked_with.lower() == "bj":
            game = "Blackjack"
        elif ctx.invoked_with.lower() == "hc":
            game = "Hot/Cold"
        elif ctx.invoked_with.lower() == "dd":
            game = "Dice Duels"
        else:
            game = "Flower Poker"

        embed = Embed(
            title=game,
            description=f"**{self.plur_simple(amount, 'token')}** have been removed from your balance.",
        )

        await channel.send(
            f"{ctx.guild.get_role(self.bot.config.roles['host']).mention}, {ctx.author.mention} would like to play "
            f"**{game}** for  **{self.plur_simple(amount, 'token')}**",
            embed=embed,
        )
        return await self._get_calls(channel, amount, commission=commission)

    async def _create_game_room(self, ctx) -> discord.TextChannel:
        game_room = self.bot.get_channel(self.config.categories["game_room"])

        host = ctx.guild.get_role(self.config.roles["host"])
        game_number = get_unique_number(self)
        self.bot.game_numbers.add(game_number)

        return await ctx.guild.create_text_channel(
            name=game_number,
            category=game_room,
            overwrites={
                ctx.author: discord.PermissionOverwrite(send_messages=True),
                host: discord.PermissionOverwrite(send_messages=True),
                ctx.guild.default_role: discord.PermissionOverwrite(send_messages=False),
            },
        )

    async def _fp_roll(
        self, row: asyncpg.Record, channel: discord.TextChannel, author: discord.Member, host: bool = False
    ) -> int:
        if not host:
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
            name="House" if host else author.display_name,
            value=f"{''.join([self.config.flowers[flower].emoji for flower in flowers])}\n{values[1]}",
        )
        embed.set_footer(text=f"Seed: {row['seed']} • Rolls: {rolls['rolls']} " f"• Nonces: {rolls['nonces']}")
        if not host:
            embed.set_author(name=author.display_name, icon_url=author.avatar_url)
        await channel.send(embed=embed)
        await self.bot.get_channel(self.config.channels["rolls_history"]).send(embed=embed)
        return values[0]

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


def setup(bot):
    bot.add_cog(HouseCog(bot))
