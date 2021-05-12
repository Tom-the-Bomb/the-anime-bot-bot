import ujson
import asyncpg
import random

import discord
from discord.ext import commands

BOBO = "<:bobo:842187511471145021>"
class Currency(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def cog_before_invoke(self, ctx):
        opened = await self.open_account(ctx.author.id)
        if opened:
            await ctx.send(f"hi {ctx.author.mention} I have created a bobo basket for you and I made the bank person to make a account for you have fun.")

    
    async def open_account(self, user_id):
        try:
            await self.bot.db.execute("INSERT INTO economy VALUES ($1, $2, $2, $2)", user_id, 0)
            return True
        except asyncpg.UniqueViolationError:
            return False

    async def get_balance(self, user_id):
        bal = await self.bot.db.fetchrow("SELECT * FROM economy WHERE user_id = $1", user_id)
        return bal["basket"], bal["bank"]

    async def change_balance(self, user_id, amount, type_="basket"):
        if type_ == "basket":
            return await self.bot.db.fetchval("UPDATE economy SET basket = $2 + basket WHERE user_id = $1 RETURNING basket", user_id, amount)
        else:
            return await self.bot.db.fetchval("UPDATE economy SET bank = $2 + bank WHERE user_id = $1 RETURNING bank", user_id, amount)
    
    @commands.command(aliases=["bal"])
    async def balance(self, ctx):
        basket, bank = await self.get_balance(ctx.author.id)
        embed = discord.Embed(color=self.bot.color, title=f"{ctx.author.name}'s balance")
        embed.add_field(name=f"{bobo} Basket", value=basket, inline=False)
        embed.add_field(name=f"{bobo}Bank", value=bank, inline=False)
        await ctx.send(embed=embed)
    

def setup(bot):
    bot.add_cog(Currency(bot))
