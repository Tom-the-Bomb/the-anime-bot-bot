import discord
from discord.ext import commands


def setup(bot):
    from utils.subclasses import AnimeContext

    bot.context = AnimeContext


def teardown(bot):
    bot.context = commands.Context
