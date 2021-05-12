import discord
from discord.ext import commands, tasks
import config
from utils.subclasses import AnimeContext
import os
import asyncio
import time
from contextlib import suppress
import aiohttp
from aiohttp import web
import quart
from quart import abort
from hypercorn.asyncio import serve
from hypercorn.config import Config
from quart import Quart

# app = Quart("vote_manager")
# shut_down = asyncio.Event()


class VoteManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.app = web.Application()
        self.bot.loop.create_task(self.run())

    def cog_unload(self):
        self.bot.loop.create_task(self._webserver.stop())
    
    async def index(self):
        return web.Response(text="hello o")
    

    async def run(self):
        self.app.router.add_get("/", self.index)
        runner = web.AppRunner(self.app, print=None)
        await runner.setup()
        self._webserver = web.TCPSite(runner, "0.0.0.0", "15000")
        await self._webserver.start()

    
    # @app.route("/")
    # async def index(self):
    #     return {"hello": "o"}

def setup(bot):
    bot.add_cog(VoteManager(bot))