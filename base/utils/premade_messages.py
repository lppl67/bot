import discord


def token_conversion_message(ctx) -> discord.Embed:
    embed = discord.Embed(
        title="Conversion Error", description="There was an error converting your amount to tokens.", color=0xFF0000
    )
    embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
    return embed


def not_enough_message(ctx) -> discord.Embed:
    embed = discord.Embed(
        title="Currency Error", description=f"Sorry {ctx.author.mention}, you don't have enough tokens!", color=0xFF0000
    )
    embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
    return embed
