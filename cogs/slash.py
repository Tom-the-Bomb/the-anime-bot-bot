import discord
from discord.ext import commands
import asyncio
import time
import discord_slash
from discord_slash import cog_ext, SlashContext

class slash(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @cog_ext.cog_slash()
    async def think(self, ctx, seconds: int):
        await ctx.defer()
        if seconds >= 899:
            return await ctx.send("how am i suppose to think for more then 15 minutes")
        await asyncio.sleep(seconds)
        await ctx.send(f"I thinked for {seconds}")

    @cog_ext.cog_slash(name="ping")
    async def ping(self, ctx):
        start = time.perf_counter()
        await ctx.defer()
        end = time.perf_counter()
        final_latency = end - start
        start=time.perf_counter()
        await self.bot.db.fetch("SELECT 1")
        postgres = time.perf_counter()-start
        postgres = round(postgres*1000)
        embed = discord.Embed(color=self.bot.color)
        embed.set_author(name="ping")
        embed.add_field(name="<:stab:744345955637395586>  websocket latency",
                        value=f"```{round(self.bot.latency * 1000)} ms ```")
        embed.add_field(name="<:postgres:821095695746203689> Postgre sql latency", value=f"```{postgres} ms```")
        embed.add_field(name="<a:typing:597589448607399949> API latency",
                        value=f"```{round(final_latency * 1000)} ms ```")
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(slash(bot))