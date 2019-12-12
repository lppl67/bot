#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilities used in several places.
"""
import datetime
import inspect
import os

from discord.ext import commands


def relative_to_here(*bits):
    """Makes a path relative to the caller function's parent directory."""
    frame = None
    try:
        frame = inspect.stack()[1]

        module = inspect.getmodule(frame[0])
        assert hasattr(module, "__file__"), "No __file__ attr, whelp."

        file = module.__file__

        dir_name = os.path.dirname(file)
        abs_dir_name = os.path.abspath(dir_name)

        result = os.path.join(abs_dir_name, *bits)

    except IndexError:
        raise RuntimeError("Could not find a stack record. Interpreter has " "been shot.")
    else:
        return result
    finally:
        del frame


def has_any_permission(*, owner=False, **perms):
    async def predicate(ctx):
        ch = ctx.channel
        permissions = ch.permissions_for(ctx.author)

        valid_perms = [getattr(permissions, perm, None) == value for perm, value in perms.items()]

        if any(valid_perms) or owner and ctx.author.id == await ctx.bot.get_owner():
            return True

        raise commands.MissingPermissions(perms.keys())

    return commands.check(predicate)


def pluralise(cardinality, name, suffix="s"):
    if cardinality - 1:
        return f"{cardinality} {name}{suffix}"
    else:
        return f"{cardinality} {name}"


def timedelta_str(td: datetime.timedelta):
    s = td.total_seconds()
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)
    components = {}
    if d:
        components["day"] = d
    if h:
        components["hour"] = h
    if m:
        components["minute"] = m
    if s or not components:
        components["second"] = s

    return ", ".join(pluralise(int(n), name) for name, n in components.items())


def make_progress_bar(percent):
    full = "\N{FULL BLOCK}"
    empty = "\N{FIGURE SPACE}"
    percent_per_block = 5

    return "".join(full if i < percent else empty for i in range(0, 100, percent_per_block))
