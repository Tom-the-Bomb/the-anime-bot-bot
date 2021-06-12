import asyncio
import os
import time
from contextlib import suppress

import aiohttp
import config
import discord
from discord.ext import commands, tasks
from utils.subclasses import AnimeContext


class Web(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.func.start(bot)

    async def main(self):
        async with self.bot.session.ws_connect("wss://gateway.botlist.space") as ws:
            self.bot.loop.create_task(self.identify(ws))
            self.bot.loop.create_task(self.heartbeat(ws))
            async for _ in ws:
                pass

    async def identify(self, ws):
        payload = {
            "op": 0,
            "t": time.time(),
            "d": {"tokens": [config.botlist_space]},
        }
        await ws.send_json(payload)

    async def heartbeat(self, ws):
        while True:
            payload = {"op": 1, "t": time.time(), "d": {}}
            await ws.send_json(payload)
            await asyncio.sleep(45)

    @tasks.loop(minutes=1)
    async def func(self, bot):
        try:
            async with bot.session.get("https://api.botlist.space/v1/bots") as resp:
                bot.botlist = await resp.text()
        except:
            pass


def setup(bot):
    bot.add_cog(Web(bot))
