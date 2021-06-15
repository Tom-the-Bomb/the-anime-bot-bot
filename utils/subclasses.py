import asyncio
import itertools
import os
import subprocess
import sys
import logging
import time
from systemd.journal import JournalHandler
import warnings
from collections import Counter, OrderedDict

import aiohttp
import aiozaneapi
import alexflipnote
import asyncpg
import config
import discord
import eight_ball
import mystbin
import psutil
import ujson
import vacefron
from asyncdagpi import Client
from discord.ext.commands.cooldowns import MaxConcurrency
from discord_slash import SlashCommand

from utils.asyncstuff import asyncexe
from utils.utils import utils

alexflipnote_ = str(config.alex_)
ipc_key = str(config.ipc_key)
zane_api = str(config.zane_api)
TOKEN_ACCESS = str(config.TOKEN_ACCESS)
api_token = str(config.api_token)
import re

from discord.ext import commands

token = re.compile(r"([a-zA-Z0-9]{24}\.[a-zA-Z0-9]{6}\.[a-zA-Z0-9_\-]{27}|mfa\.[a-zA-Z0-9_\-]{84})")


class AnimeContext(commands.Context):
    def __init__(self, *args, **kwargs):
        self.utils = utils
        super().__init__(*args, **kwargs)

    async def comfrim(self, content=None, timeout=60, **kwargs):
        m = await self.send(content=content, **kwargs)
        await m.add_reaction(self.bot.get_emoji(852031038024056833))
        await m.add_reaction(self.bot.get_emoji(852031063140073502))
        try:
            r = await self.bot.wait_for(
                "raw_reaction_add",
                check=lambda x: x.message_id == m.id
                and x.user_id == self.author.id
                and x.emoji.is_custom_emoji()
                and x.emoji.id in (852031038024056833, 852031063140073502),
            )
        except asyncio.TimeoutError:
            return False
        return r.emoji.id == 852031038024056833

    async def remove(self, *args, **kwargs):
        m = await self.send(*args, **kwargs)
        await m.add_reaction("\U0000274c")
        await self.bot.wait_for(
            "reaction_add",
            check=lambda i, v: i.message.id == m.id and v.id == self.message.author.id and i.emoji == "\U0000274c",
        )
        await m.delete()

    @discord.utils.cached_property
    def replied_reference(self):
        ref = self.message.reference
        if ref and isinstance(ref.resolved, discord.Message):
            return ref.resolved.to_reference()
        return None

    @staticmethod
    def big_embed():
        embed = discord.Embed(color=0x00FF6A, title="a" * 256, description="a" * 2048)
        embed.add_field(name="a" * 256, value="a" * 112)
        embed.add_field(name="a" * 256, value="a" * 1024)
        embed.set_footer(text="a" * 2048)
        return embed

    async def ovoly(self, msg):
        ovo = msg.replace("l", "v").replace("L", "v").replace("r", "v").replace("R", "v")
        return f"{ovo} ovo"

    async def get_paste(self, link):
        try:
            return str(await self.bot.mystbin.get(link))
        except mystbin.BadPasteID:
            return None

    async def paste(self, content):
        return str(await self.bot.mystbin.post(content))

    async def send(self, content=None, *, codeblock=False, lang="py", **kwargs):
        # if self.invoked_with("jishaku"):
        #   embed = discord.Embed(color=0x2ecc71, description=content)
        #   message = super().send(content=None, embed=embed)
        #   return message
        if codeblock:
            content = f"```{lang}\n" + str(content) + "\n```"
        if self.message.id in self.bot._message_cache:
            if self.message.edited_at:
                msg = self.channel.get_partial_message(self.bot._message_cache[self.message.id])
                if kwargs.get("file"):
                    m = await super().send(content, nonce=os.urandom(12).hex(), **kwargs)
                    self.bot._message_cache[self.message.id] = m.id
                    try:
                        self.bot.to_delete_message_cache[self.message.id].append(m.id)
                    except KeyError:
                        pass
                    return m
                await msg.edit(content=content, **kwargs)
                return msg
            else:
                message = await super().send(content, nonce=os.urandom(12).hex(), **kwargs)
                try:
                    self.bot.to_delete_message_cache[self.message.id].append(message.id)
                except KeyError:
                    pass
                return message
        else:
            message = await super().send(content, nonce=os.urandom(12).hex(), **kwargs)
            self.bot._message_cache[self.message.id] = message.id
            self.bot.to_delete_message_cache[self.message.id] = discord.utils.SnowflakeList((message.id, ))
            return message

    async def reply(self, content=None, *, codeblock=False, lang="py", **kwargs):
        if codeblock:
            content = f"```{lang}\n" + str(content) + "\n```"
        if self.message.id in self.bot._message_cache:
            if self.message.edited_at:
                msg = self.channel.get_partial_message(self.bot._message_cache[self.message.id])
                if kwargs.get("file"):
                    m = await super().reply(content, nonce=os.urandom(12).hex(), **kwargs)
                    self.bot._message_cache[self.message.id] = m.id
                    try:
                        self.bot.to_delete_message_cache[self.message.id].append(m.id)
                    except KeyError:
                        pass
                    return m
                if not kwargs.get("allowed_mentions"):
                    msg = await msg.edit(
                        content=content,
                        allowed_mentions=discord.AllowedMentions.none(),
                        **kwargs,
                    )
                else:
                    msg = await msg.edit(content=content, **kwargs)
                return msg
            else:
                message = await super().reply(content, nonce=os.urandom(12).hex(), **kwargs)
                try:
                    self.bot.to_delete_message_cache[self.message.id].append(message.id)
                except KeyError:
                    pass
                return message
        else:
            message = await super().reply(content, nonce=os.urandom(12).hex(), **kwargs)
            self.bot._message_cache[self.message.id] = message.id
            self.bot.to_delete_message_cache[self.message.id] = discord.utils.SnowflakeList((message.id, ))
            return message

class InvalidImage(Exception):
    pass


class AnimeMessage(discord.Message):
    pass


class GlobalCooldown(commands.CommandOnCooldown):
    pass


async def prefix_get(bot, message):
    if message.guild is None:
        return ["<@787927476177076234>", "<@!787927476177076234>"] + bot.default_prefix
    if bot.prefixes.get(message.guild.id):
        return ["<@787927476177076234>", "<@!787927476177076234>"] + bot.prefixes.get(message.guild.id)
    if not bot.prefixes.get(message.guild.id):
        await bot.db.execute(
            "INSERT INTO prefix (guild_id, prefix) VALUES ($1, $2) ON CONFLICT (guild_id) DO NOTHING",
            message.guild.id,
            bot.default_prefix,
        )
        bot.prefixes[message.guild.id] = bot.default_prefix
        return ["<@787927476177076234>", "<@!787927476177076234>"] + bot.prefixes[message.guild.id]
    return ["<@787927476177076234>", "<@!787927476177076234>"] + bot.default_prefix


class LimitedSizeDict(OrderedDict):
    def __init__(self, *args, **kwds):
        self.size_limit = 1000
        OrderedDict.__init__(self, *args, **kwds)
        self._check_size_limit()

    def __setitem__(self, key, value):
        OrderedDict.__setitem__(self, key, value)
        self._check_size_limit()

    def _check_size_limit(self):
        if self.size_limit is not None:
            while len(self) > self.size_limit:
                self.popitem(last=True)


class AnimeBot(commands.Bot):
    def __init__(self):
        self.connector = aiohttp.TCPConnector(limit=200)
        self.logger = logging.getLogger("TheAnimeBot")
        self.logger.addHandler(JournalHandler())
        intents = discord.Intents.default()
        intents.members = True
        # self.ipc = ipc.Server(self, secret_key=ipc_key)
        self.command_list = []
        super().__init__(
            command_prefix=prefix_get,
            max_messages=1000,
            connector=self.connector,
            intents=intents,
            description=r"""
|_   _| |__   ___     / \   _ __ (_)_ __ ___   ___  | __ )  ___ | |_ 
  | | | '_ \ / _ \   / _ \ | '_ \| | '_ ` _ \ / _ \ |  _ \ / _ \| __|
  | | | | | |  __/  / ___ \| | | | | | | | | |  __/ | |_) | (_) | |_ 
  |_| |_| |_|\___| /_/   \_\_| |_|_|_| |_| |_|\___| |____/ \___/ \__|
""",
            chunk_guilds_at_startup=False,
            case_insensitive=True,
            allowed_mentions=discord.AllowedMentions.none(),
            strip_after_prefix=True,
        )

    def add_command(self, command):
        super().add_command(command)
        command.cooldown_after_parsing = True
        if not getattr(command._buckets, "_cooldown", None):
            command._buckets = commands.CooldownMapping.from_cooldown(1, 3, commands.BucketType.user)
        if command._max_concurrency is None:
            command._max_concurrency = MaxConcurrency(1, per=commands.BucketType.user, wait=False)

    async def create_cache(self):
        prefixes = await self.db.fetch("SELECT * FROM prefix")
        for i in prefixes:
            self.prefixes[i["guild_id"]] = i["prefix"]
        emojioptions = await self.db.fetch("SELECT * FROM emojioptions")
        if emojioptions:
            for i in emojioptions:
                self.emojioptions[i["user_id"]] = i["enabled"]
        commandsusage = await self.db.fetch("SELECT * FROM commandsusage")
        for i in commandsusage:
            self.commandsusages[i["command"]] = i["usages"]
            self.command_counter += i["usages"]
        socket = await self.db.fetch("SELECT * FROM socket")
        for i in socket:
            self.socket_stats[i["name"]] = i["count"]
            self.socket_receive += i["count"]
        blacklist = await self.db.fetch("SELECT * FROM blacklist")
        if blacklist:
            for i in blacklist:
                self.blacklist[i["user_id"]] = i["reason"]
        return True

    async def getch(self, id):
        user = self.get_user(id)
        if not user:
            user = await self.fetch_user(id)

        return user

    async def is_blacklisted(self, ctx):
        return ctx.author.id not in self.blacklist

    async def chunk_(self, ctx):
        if ctx.guild and not ctx.guild.chunked:
            await ctx.guild.chunk()

    async def before_invoke_(self, ctx):
        try:
            if ctx.message.author.id in [590323594744168494, 711057339360477184]:
                await ctx.command._max_concurrency.release()
        except:
            pass
        if not ctx.command.qualified_name.startswith("jishaku"):
            await ctx.trigger_typing()
        ctx.bot.loop.create_task(self.chunk_(ctx))
    
    async def initialize_constants(self):
        self.default_prefix = ["ovo "]
        self.context = AnimeContext
        self.prefixes = {}
        self.emojioptions = {}
        self.blacklist = {}
        self.url_regex = re.compile(
            r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
            re.IGNORECASE,
        )
        self.bad_word_cache = {}
        self.logging_cache = {}
        self.logging_webhook_cache = []
        self.utils = utils
        self.deleted_message_cache = LimitedSizeDict()
        self.concurrency = []
        self.color = 0xFF4500
        self.psutil_process = psutil.Process()
        self.to_delete_message_cache = {}
        self._message_cache = {}
        self.prefixes = {}
        self.socket_receive = 0
        self.start_time = time.time()
        self.socket_stats = Counter()
        self.command_counter = 0
        self.commandsusages = Counter()
        self.session = aiohttp.ClientSession(
            headers={
                "User-Agent": f"python-requests/2.25.1 The Anime Bot/1.1.0 Python/{sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]} aiohttp/{aiohttp.__version__}"
            },
            connector=self.connector,
            json_serialize=ujson.dumps,
            timeout=aiohttp.ClientTimeout(total=10),
        )
    
    def initialize_libaries(self):
        self.mystbin = mystbin.Client(session=self.session)
        self.vacefron_api = vacefron.Client(session=self.session, loop=self.loop)
        self.dag = Client(api_token, session=self.session, loop=self.loop)
        self.alex = alexflipnote.Client(alexflipnote_, session=self.session, loop=self.loop)
        self.ball = eight_ball.ball()
        self.zaneapi = aiozaneapi.Client(zane_api)
    
    def load_all_extensions(self):
        for file in os.listdir("./cogs"):
            if file.endswith(".py"):
                try:
                    self.load_extension(f"cogs.{file[:-3]}")
                except Exception as e:
                    self.logger.critical(f"Unable to load cog: {file}, ignoring. Exception: {e}")

    def unload_all_extensions(self):
        for file in os.listdir("./cogs"):
            if file.endswith(".py"):
                try:
                    self.unload_extension(f"cogs.{file[:-3]}")
                except Exception as e:
                    self.logger.critical(f"Unable to unload cog: {file}, ignoring. Exception: {e}")


    def run(self, *args, **kwargs):
        # self.ipc.start()
        db = self.loop.run_until_complete(
            asyncpg.create_pool(
                host="localhost",
                port="5432",
                user="postgres1",
                password="postgres",
                database="cryptex",
                min_size=10,
                max_size=20,
            )
        )
        self.db = db
        self.loop.run_until_complete(self.initialize_constants()) # I know there are no reason for this to be async but I want it to stop spamming that not created in loop error
        self.initialize_libaries()
        self.loop.run_until_complete(self.create_cache())
        self.load_all_extensions()
        self.add_check(self.is_blacklisted)
        self.before_invoke(self.before_invoke_)
        super().run(*args, **kwargs)

    async def close(self):
        self.unload_all_extensions()
        try:
            await asyncio.wait_for(self.db.close(), timeout=10)
        except (asyncio.TimeoutError, Exception):
            self.db.terminate()
        await self.loop.shutdown_default_executor()
        await self.session.close()
        await super().close()

    def get_message(self, message_id):
        return self._connection._get_message(message_id)

    async def get_context(self, message, *, cls=None):
        return await super().get_context(message, cls=self.context)
