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
    
    async def topgg(self, request):
        if not request.headers.get("Authorization"):
            return web.Response(status=401, text="Unauthorized")
        if request.headers.get("Authorization") != config.vote_webhook_token:
            return web.Response(status=401, text="Unauthorized")
        data = await request.json()
        try:
            user = await self.bot.getch(data["user"])
            vote_counts = await self.bot.db.fetchval(
                (
                    "INSERT INTO votes VALUES ($1, $2)"
                    " ON CONFLICT (user_id) "
                    "DO UPDATE count = votes.count + 1"
                    " RETURNING count"
                ),
                user.id,
                1,
            )
            await user.send(f"Hey, {user.mention} Thanks for voting it mean a lot this is your {vote_counts} voting for The Anime Bot thank you so much.")
            await self.bot.get_channel(791518421920907265).send(f"{user.mention}, just upvoted our bot this is their {vote_counts} voting for The Anime Bot")
        except:
            return web.Response(status=500)
        return web.Response(status=200, text="OK")

    async def index(self, request):
        return web.Response(text="anime bot is the best bot")
    

    async def run(self):
        await self.bot.wait_until_ready()
        self.app.router.add_get("/", self.index)
        self.app.router.add_post("/topgg", self.topgg)
        runner = web.AppRunner(self.app)
        await runner.setup()
        self._webserver = web.TCPSite(runner, "0.0.0.0", "15000")
        await self._webserver.start()

    
    # @app.route("/")
    # async def index(self):
    #     return {"hello": "o"}

def setup(bot):
    bot.add_cog(VoteManager(bot))
