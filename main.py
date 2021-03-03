import asyncio
import difflib
import functools
import logging
import os
import re
import sys
import traceback
import warnings

import aioredis
import uvloop

import discord
from discord.ext import commands
from discord_slash import SlashCommand
from utils.HelpPaginator import CannotPaginate, HelpPaginator
from utils.subclasses import AnimeBot

logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)


asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

warnings.filterwarnings("ignore", category=DeprecationWarning)
os.system("python3 webserver.py &")
os.system("python3 hmm.py &")
TOKEN = os.getenv("TOKEN")


bot = AnimeBot()
slash = SlashCommand(bot, sync_commands=True,
                     sync_on_cog_reload=True, override_type=True)


@slash.slash(name="wtf", guild_ids=[786359602241470464])
async def wtf(ctx):
    await ctx.respond()
    await ctx.send("wtf wtf")


os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True"
os.environ["JISHAKU_NO_UNDERSCORE"] = "True"

for file in os.listdir("./cogs"):
    if file.endswith(".py"):
        bot.load_extension(f"cogs.{file[:-3]}")

bot.run(TOKEN)
