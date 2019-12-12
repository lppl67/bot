#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from libneko.extras import superuser


class WhitelistedSuperUserCog(superuser.SuperuserCog):
    """
    This is a simple subclass of libneko's SuperUserCog that simply changes the
    owner check to include all Python Dev Co. devs.
    """

    async def cog_check(self, ctx):
        """Filter for who can run the exec command"""
        return ctx.bot.owner_id == ctx.author.id


def setup(bot):
    bot.add_cog(WhitelistedSuperUserCog())
