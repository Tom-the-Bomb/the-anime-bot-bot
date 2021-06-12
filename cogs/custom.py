import copy
import datetime
import re

import aiohttp
import discord
from aiohttp import web
from discord.ext import commands
from utils.subclasses import AnimeContext


class Custom(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.invite_regex = re.compile(r"(?:https?://)?discord(?:app)?\.(?:com/invite|gg)/[a-zA-Z0-9]+/?")
        self.app = web.Application()
        self.bot.loop.create_task(self.run())

    def cog_unload(self):
        self.bot.loop.create_task(self._webserver.stop())

    # @commands.Cog.listener()
    # async def on_raw_message_edit(self, payload):
    #     if payload.data and payload.data.get("guild_id") and int(payload.data.get("guild_id")) == 801896886604529734 and payload.data.get("content") and self.bot.invite_regex.findall(payload.data.get("content"), re.IGNORECASE):
    #         await self.bot.http.delete_message(int(payload.data.get("channel_id")), int(payload.data.get("id")))

    # @commands.Cog.listener()
    # async def on_message(self, message):
    #     if message.guild and message.guild.id == 801896886604529734 and self.bot.invite_regex.findall(message.content, re.IGNORECASE):
    #         await message.delete()

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild.id == 786359602241470464:
            if member.bot:
                await member.add_roles(discord.Object(786369068834750466))
            else:
                await member.add_roles(discord.Object(792645158495453204))
        if member.guild.id == 796459063982030858 and member.bot:
            await member.add_roles(discord.Object(833132759361912842))

    async def index(self, request):
        b = await request.read()
        return web.Response(status=200, body=b)

    async def run(self):
        await self.bot.wait_until_ready()
        self.app.router.add_route("*", "/", self.index)
        runner = web.AppRunner(self.app)
        await runner.setup()
        self._webserver = web.TCPSite(runner, "127.0.0.1", "15500")
        await self._webserver.start()


def setup(bot):
    bot.add_cog(Custom(bot))
