import json
import random

import aiofiles
from discord.ext import commands

from base.core.base_cog import BaseCog
from base.utils.embeds import Embed


class Admin(BaseCog):
    """Admin Commands"""

    def __init__(self, bot):
        super().__init__(bot)

        self.bot.loop.create_task(self._get_raffles())

    async def _get_raffles(self):
        try:
            async with aiofiles.open("raffles.json", "r") as fp:
                self.bot.raffles = json.loads(await fp.read())
            self.logger.info("Loading previous raffles.")
        except FileNotFoundError:
            self.logger.info("No open raffles found.")

    @commands.has_role("Hosts")
    @commands.command()
    async def startraffle(self, ctx, ticket_price, tickets: int):
        """Starts a raffle."""
        price = await self.convert_to_tokens(ctx, ticket_price.lower())
        if price <= 0:
            return

        raffle_number = random.choice(list(set(range(1_000, 9_999)) - set(self.bot.raffles.keys())))
        self.bot.raffles.update({str(raffle_number): {"price": price, "tickets": tickets, "members": list()}})

        async with aiofiles.open("raffles.json", "w") as fp:
            await fp.write(json.dumps(self.bot.raffles))

        await ctx.guild.create_role(name=str(raffle_number))

        await ctx.send(
            embed=Embed(
                title="Raffle Successfully Created",
                description=f"Raffle {raffle_number} was successfully created with "
                f"{self.plur_simple(tickets, 'ticket')} with a price of {self.plur_simple(price, 'token')} per ticket.",
            )
        )


def setup(bot):
    bot.add_cog(Admin(bot))
