import discord
from discord.ext import commands
import aiohttp
from aiohttp import web
from utils.subclasses import AnimeContext
import copy
import datetime


class Custom(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.app = web.Application()
        self.bot.loop.create_task(self.run())

    def cog_unload(self):
        self.bot.loop.create_task(self._webserver.stop())

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
