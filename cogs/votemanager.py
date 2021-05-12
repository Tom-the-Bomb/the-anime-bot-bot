import discord
from discord.ext import commands, tasks
import config
from utils.subclasses import AnimeContext
import os
import asyncio
import time
from contextlib import suppress
import aiohttp
import quart
from quart import abort
from hypercorn.asyncio import serve
from hypercorn.config import Config
from quart import Quart

app = Quart("vote_manager")
shut_down = asyncio.Event()


class VoteManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.app = app
    
    @app.route("/")
    async def index(self):
        return {"hello": "o"}
    
    # @app.route("/topgg")
    # async def topgg(self):
    #     auth = request.headers["Authorization"]
    #     if auth != config.vote_webhook_token:

def teardown(bot):
    app.shutdown()
    shut_down.set()

def setup(bot):
    bot.add_cog(VoteManager(bot))
    # config = Config()
    # config.bind = ["0.0.0.0:50000"]
    bot.loop.create_task(app.run("0.0.0.0", "50000"))
