import asyncio
import uvloop

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

from systemd import journal
from systemd.journal import JournalHandler

import tracemalloc

tracemalloc.start()
import difflib
import config
import functools
import logging
import os
import re
import sys
import traceback
import warnings

import aioredis

import discord
from discord.ext import commands
from discord_slash import SlashCommand
from utils.HelpPaginator import CannotPaginate, HelpPaginator
from utils.subclasses import AnimeBot

sys.stdout = journal.stream()

logger = logging.getLogger("discord")
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))
logger.addHandler(handler)
logger.addHandler(JournalHandler())


warnings.filterwarnings("ignore", category=DeprecationWarning)


bot = AnimeBot()
slash = SlashCommand(bot, sync_commands=True, sync_on_cog_reload=True, override_type=True)


bot.owner_ids = [711057339360477184, 590323594744168494]

os.environ["NO_COLOR"] = "True"
os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True"
os.environ["JISHAKU_NO_UNDERSCORE"] = "True"

bot.run(config.token)
