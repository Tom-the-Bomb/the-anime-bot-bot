import asyncio
import re

import discord
from discord.ext import commands, tasks
import ujson

EMOJI_REGEX = re.compile(r'<a?:.+?:([0-9]{15,21})>')

class Emoji(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.to_save = {}
        self.save_lock = asyncio.Lock()
        self._task = self.save_stats.start()
    
    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild:
            return
        if message.author.bot:
            return
        matches = EMOJI_REGEX.findall(message.content)
        if not matches:
            return
        async with self.save_lock:
            if not self.to_save.get(message.guild.id):
                self.to_save[message.guild.id] = {}
            for i in matches:
                if not self.bot.get_emoji(int(i)):
                    continue
                c = self.to_save[message.guild.id].get(i, 0)
                self.to_save[message.guild.id][i] = c + 1

    def cog_unload(self):
        self._task.cancel()
    
    @tasks.loop(seconds=10)
    async def save_stats(self):
        await self.bot.wait_until_ready()
        async with self.save_lock:
            sql = "INSERT INTO emoji_stats VALUES ($1, $2) ON CONFLICT (guild_id) DO UPDATE SET emojis = merge_json(emojis, $2)"
            for i, v in self.to_save.items():
                j = ujson.dumps(v, ensure_ascii=True, escape_forward_slashes=False)
                await self.bot.db.execute(sql, i, j)
            self.to_save = {}
    
    @commands.command()
    async def emojistats(self, ctx):
        stats = await self.bot.db.fetch("SELECT * FROM emoji_stats")
        merged = []
        for i in stats:
            s = ujson.loads(i["emojis"])
            merged += sorted(list(s.items()), key=lambda x: x[1], reverse=True)
        final = sorted(merged, key=lambda x: x[1], reverse=True)
        to_format = [f"{str(self.bot.get_emoji(int(i)))} - {v} uses" for i, v in final][:10]
        embed = discord.Embed(color=self.bot.color, title="Emoji Stats", description="\n".join(to_format))
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(Emoji(bot))





        


