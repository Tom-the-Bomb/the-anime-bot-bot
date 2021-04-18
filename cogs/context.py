import discord
from discord.ext impot commands
from utils.subclasses import AnimeContext

def setup(bot):
    bot.context = AnimeContext

def teardown(bot):
    bot.context = commands.Context