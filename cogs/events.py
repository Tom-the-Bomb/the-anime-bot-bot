import asyncio
import datetime
import gc
import json
import logging
import os
import time
import tracemalloc
import zipfile
from contextlib import suppress
from csv import writer
from io import BytesIO
from pathlib import Path

import aiofile
import aiozaneapi
import asyncdagpi
import config
import discord
import humanize
import PIL
import prettify_exceptions
import ratelimiter
import ujson
import wavelink
from discord.ext import commands, tasks
from PIL import Image
from utils.asyncstuff import asyncexe
from utils.fuzzy import finder
from utils.subclasses import AnimeContext, GlobalCooldown

logging.getLogger("asyncio").setLevel(logging.CRITICAL)

authorizationdeal = config.gists


discord_bot_list = config.discord_bot_list
bots_for_discord = config.bots_for_discord
topgg = config.topgg
discord_extreme_list = config.discord_extreme_list
botlist_space = config.botlist_space
POSTGRE_DATABASE_URL = config.POSTGRE_DATABASE_URL


class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.ws_recieved = 0
        self.ratelimiter = ratelimiter.RateLimiter(max_calls=1, period=3)

        self.bot.send = 0
        with suppress(RuntimeError):
            self.send_files.start()
            self.clean_up.start()
            self.gists.start()
            self.status.start(bot)
            self.graph.start()
            self.post.start(bot)
            self.update.start(bot)
            self.post.start()
        self.errors_list = []
        self.bot.counter = 0

    def cog_unload(self):
        with suppress(RuntimeError):
            self.send_files.cancel()
            self.clean_up.cancel()
            self.gists.cancel()
            self.status.cancel()
            self.graph.cancel()
            self.post.cancel()
            self.update.cancel()
            self.post.cancel()

    @staticmethod
    def files_zip():
        file_1 = BytesIO()
        with zipfile.ZipFile(file_1, mode="w") as zipfile_:
            p = Path(".")
            for i in p.iterdir():
                if not i.is_dir() and i.name != "config.py":
                    with i.open(encoding="utf-8") as f:
                        try:
                            zipfile_.writestr(i.name, f.read())
                        except ValueError:
                            continue

        file_1.seek(0)
        return file_1

    @tasks.loop(minutes=2)
    async def send_files(self):
        await self.bot.wait_until_ready()
        f_1 = await asyncio.to_thread(self.files_zip)
        f_log = discord.File("discord.log")
        try:
            await self.bot.get_channel(836756007761608734).send(
                files=[
                    discord.File(f_1, "cogs.zip"),
                    f_log,
                ]
            )
        except discord.HTTPException:
            return
        # if not hasattr(self.bot, "cool_webhooks"):
        #     self.bot.cool_webhooks = await self.bot.get_channel(836756007761608734).webhooks()
        # for _ in range(2):
        #     for i in self.bot.cool_webhooks:
        #         async with self.ratelimiter:
        #             await i.send(
        #                 file=discord.File(BytesIO(os.urandom(8388608 - 1000)), "thing.somethingy"),
        #                 wait=True,
        #             )

    @tasks.loop(minutes=1)
    async def clean_up(self):
        await asyncio.to_thread(gc.collect)
        await asyncio.to_thread(tracemalloc.clear_traces)

    @tasks.loop(minutes=30)
    async def gists(self):
        await self.bot.wait_until_ready()
        date = datetime.datetime.now() - datetime.timedelta(hours=8)
        date = f"{date.month} " f"{date.day} " f"{date.year} " f"{date.hour}:" f"{date.minute}:" f"{date.second}"
        async with aiofile.async_open("discord.log", "r") as f:
            content = await f.read()
        data = {
            "public": False,
            "description": date,
            "files": {"discord.log": {"content": content}},
        }
        async with self.bot.session.post(
            "https://api.github.com/gists",
            headers={
                "Authorization": f"{authorizationdeal}",
                "Accept": "application/vnd.github.inertia-preview+json",
            },
            json=data,
        ) as resp:
            pass

    @tasks.loop(seconds=30)
    async def graph(self):
        await self.bot.wait_until_ready()
        with open("socket.csv", "a") as f:
            writer_object = writer(f)

            writer_object.writerow(
                [
                    self.bot.socket_stats["MESSAGE_CREATE"],
                    self.bot.socket_stats["GUILD_MEMBER_UPDATE"],
                    self.bot.socket_stats["TYPING_START"],
                ]
            )

            f.close()

    @tasks.loop(minutes=1)
    async def status(self, bot):
        await bot.wait_until_ready()
        await bot.change_presence(activity=discord.Game(name=f"{len(bot.guilds)} guilds and {len(bot.users)} users"))

    @tasks.loop(minutes=5)
    async def update(self, bot):
        try:
            await bot.wait_until_ready()
            message = bot.get_channel(809204640054640641).get_partial_message(809205344814891040)
            current_time = time.time()
            lists = []
            difference = int(current_time - bot.start_time) / 60
            lists.append(f"Received {bot.socket_receive} {bot.socket_receive//difference} per minute")
            for i, (n, v) in enumerate(bot.socket_stats.most_common()):
                lists.append(f"{n:<30} {v:<20} {round(v/difference, 3)} /minute")
            lists = "\n".join(lists)
            await message.edit(content=f"```\n{lists}\n```")
        except discord.HTTPException:
            pass

    @tasks.loop(minutes=1)
    async def post(self, bot):
        await bot.wait_until_ready()
        async with bot.session.post(
            "https://top.gg/api/bots/787927476177076234/stats",
            headers={"Authorization": topgg},
            data={"server_count": len(bot.guilds)},
        ):
            pass

        async with bot.session.post(
            "https://discordbotlist.com/api/v1/bots/anime-quotepic-bot/stats",
            headers={"Authorization": discord_bot_list},
            data={
                "voice_connections": len(bot.voice_clients),
                "users": len(bot.users),
                "guilds": len(bot.guilds),
            },
        ):
            pass
        async with bot.session.post(
            "https://api.discordextremelist.xyz/v2/bot/787927476177076234/stats",
            headers={
                "Authorization": discord_extreme_list,
                "Content-Type": "application/json",
            },
            json={
                "guildCount": len(bot.guilds),
            },
        ):
            pass
        async with bot.session.post(
            "https://botsfordiscord.com/api/bot/787927476177076234",
            headers={
                "Content-Type": "application/json",
                "Authorization": bots_for_discord,
            },
            json={"server_count": len(bot.guilds)},
        ):
            pass

        async with bot.session.post(
            "https://api.botlist.space/v1/bots/787927476177076234",
            headers={
                "Authorization": botlist_space,
                "Content-Type": "application/json",
            },
            json={"server_count": len(bot.guilds)},
        ):
            pass

    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        self.bot.counter += 1

    @commands.Cog.listener()
    async def on_command(self, ctx):
        self.bot.send += 1

    @commands.Cog.listener()
    async def on_invite_delete(self, invite):
        pass

    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        pass

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        pass

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        pass

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        pass

    @commands.Cog.listener()
    async def on_guild_unavailable(self, guild):
        pass

    @commands.Cog.listener()
    async def on_guild_available(self, guild):
        pass

    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild, before, after):
        pass

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        pass

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        pass

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        pass

    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        pass

    @commands.Cog.listener()
    async def on_user_update(self, before, after):
        pass

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        pass

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        pass

    @commands.Cog.listener()
    async def on_member_join(self, member):
        pass

    @commands.Cog.listener()
    async def on_webhooks_update(self, channel):
        pass

    @commands.Cog.listener()
    async def on_guild_integrations_update(self, guild):
        pass

    @commands.Cog.listener()
    async def on_guild_channel_pins_update(self, channel, last_pin):
        pass

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        pass

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        pass

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        pass

    @commands.Cog.listener()
    async def on_private_channel_pins_update(self, channel, last_pin):
        pass

    @commands.Cog.listener()
    async def on_private_channel_update(self, before, after):
        pass

    @commands.Cog.listener()
    async def on_private_channel_create(self, channel):
        pass

    @commands.Cog.listener()
    async def on_private_channel_delete(self, channel):
        pass

    @commands.Cog.listener()
    async def on_raw_reaction_clear_emoji(self, payload):
        pass

    @commands.Cog.listener()
    async def on_reaction_clear_emoji(self, reaction):
        pass

    @commands.Cog.listener()
    async def on_raw_reaction_clear(self, payload):
        pass

    @commands.Cog.listener()
    async def on_reaction_clear(self, message, reactions):
        pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        pass

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        pass

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        pass

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        pass

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload):
        for i in payload.message_ids:
            if self.bot.to_delete_message_cache.get(i):
                del self.bot.to_delete_message_cache[i]

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        pass

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):
        if not self.bot.to_delete_message_cache.get(payload.message_id):
            return
        if payload.guild_id:
            try:
                await self.bot.http.delete_messages(
                    payload.channel_id, self.bot.to_delete_message_cache.get(payload.message_id)
                )
            except (discord.Forbidden, discord.NotFound):
                for i in self.bot.to_delete_message_cache.get(payload.message_id):
                    try:
                        await self.bot.http.delete_message(payload.channel_id, i)
                    except discord.NotFound:
                        pass
        else:
            for i in self.bot.to_delete_message_cache.get(payload.message_id):
                try:
                    await self.bot.http.delete_message(payload.channel_id, i)
                except discord.NotFound:
                    pass

        del self.bot.to_delete_message_cache[payload.message_id]

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages):
        pass

    @commands.Cog.listener()
    async def on_typing(self, channel, user, when):
        pass

    @commands.Cog.listener()
    async def on_socket_response(self, msg):
        if msg.get("op") == 7:
            print(f"\033[92mRecieved reconnect request\033[0m")
        if msg.get("op") == 9:
            print(f"\033[92mRecieved invalid session request\033[0m")
        if msg.get("op") == 10:
            print(f"\033[92mRecieved hello request\033[0m")

    @commands.Cog.listener()
    async def on_socket_response(self, payload):
        if payload.get("op") == 2:
            print(f"\033[92mSend Identify payload\033[0m")
        elif payload.get("op") == 6:
            print(f"\033[92mSend Resume payload\033[0m")

    @commands.Cog.listener()
    async def on_socket_raw_receive(self, msg):
        self.bot.ws_recieved += 1

    @commands.Cog.listener()
    async def on_shard_resumed(self, shard_id):
        pass

    @commands.Cog.listener()
    async def on_resumed(self):
        print(f"\033[92mResumed Discord session\033[0m")

    @commands.Cog.listener()
    async def on_shard_ready(self, shard_id):
        pass

    @commands.Cog.listener()
    async def on_shard_disconnect(self, shard_id):
        pass

    @commands.Cog.listener()
    async def on_disconnect(self):
        print(f"\033[93mDisconnected from Discord\033[0m")

    @commands.Cog.listener()
    async def on_shard_connect(self, shard_id):
        pass

    @commands.Cog.listener()
    async def on_connect(self):
        print(f"\033[92mConnected to Discord\033[0m")

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload):
        pass

    @commands.Cog.listener()
    async def on_message_edit(self, old, new):
        if old.embeds != []:
            return
        if new.embeds != []:
            return
        await self.bot.process_commands(new)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        channel = self.bot.get_channel(798330449058725898)
        await channel.send(f"**{guild.name}** just added the bot with **{guild.member_count}** members ")

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        try:
            channel = self.bot.get_channel(799806497118224415)
            await channel.send(f"**{guild.name}** just kicked the bot with **{guild.member_count}** members ")
        except discord.HTTPException:
            pass

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.content == "<@!787927476177076234>" and not message.author.bot:
            message_ = await message.channel.send(
                f"Hii there why u ping me smh oh i mean hii my prefix is `{', '.join(self.bot.prefixes[message.guild.id])}` "
            )
            self.bot.to_delete_message_cache[message.id] = [message_]
        if (
            message.content.startswith(";;")
            and not message.author.bot
            and self.bot.emojioptions.get(message.author.id)
        ):
            lists = []
            msg = message.content.replace(" ", "")
            emojis = msg.split(";;")
            for i in emojis:
                if not i:
                    continue
                e = finder(i, self.bot.emojis, key=lambda i: i.name, lazy=False)
                if not e:
                    continue
                e = e[0]
                if not e or not emojis:
                    continue
                if e.is_usable() != False:
                    lists.append(str(e))
            if lists != []:
                try:
                    message_ = await message.channel.send("".join(lists))
                    self.bot._message_cache[message.id] = message_.id
                    self.bot.to_delete_message_cache[message.id] = [message_.id]
                except (discord.HTTPException, KeyError):
                    pass
        # mentions = message.mentions
        # try:
        #   for x in mentions:
        #     if x == self.bot.user:
        #       with open("prefixes.json", "r") as f:
        #         prefixes = json.load(f)
        #     prefix_for_guild = prefixes[str(message.guild.id)]
        #     embed = discord.Embed(color=0x2ecc71)
        #     embed.set_author(name=f"bot prefix for this guild is   {prefix_for_guild}")
        #     embed.set_footer(text=f"requested by {message.author} response time : {round(self.bot.latency * 1000)} ms", icon_url=message.author.avatar_url)
        #     await message.channel.send(embed=embed)
        # except:
        #   pass
        # if message.channel.id == 796603184587210752:
        #   voter = await self.bot.get_user(message.content)
        #   channel = self.bot.get_channel(791518421920907265)
        #   embed = discord.Embed(color=0x2ecc71)
        #   embed.set_author(name=voter, icon_url=voter.avatar_url, url="https://top.gg/bot/787927476177076234/vote")
        #   embed.add_field(name=f"{voter} just upvoted our bot yay", value="upvote our bot here https://top.gg/bot/787927476177076234/vote", inline=False)
        #   await channel.send(embed=embed)
        #   await voter.send(embed=embed)

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.change_presence(activity=discord.Game(name=f"{len(self.bot.guilds)} guilds"))
        print(len(self.bot.guilds))
        print("Logged in as:\n{0.user.name}\n{0.user.id}".format(self.bot))


def setup(bot):
    bot.add_cog(Events(bot))
