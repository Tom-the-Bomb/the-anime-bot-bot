import ujson
import asyncpg
import random

import discord
from discord.ext import commands

BOBO = "\U0000232C"


class Currency(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def cog_before_invoke(self, ctx):
        opened = await self.open_account(ctx.author.id)
        if opened:
            await ctx.send(f"hi {ctx.author.mention} I have created a bobo basket for you and I made the bank person to make a account for you have fun.")

    
    async def open_account(self, user_id):
        try:
            await self.bot.db.execute("INSERT INTO economy VALUES ($1, $2, $2, $2)", user_id, "0")
            return True
        except asyncpg.UniqueViolationError:
            return False

    async def get_balance(self, user_id):
        bal = await self.bot.db.fetchrow("SELECT * FROM economy WHERE user_id = $1", user_id)
        return int(bal["basket"]), int(bal["bank"])

    async def change_balance(self, user_id, amount, type_="basket"):
        basket, bank = await self.get_balance(user_id)
        if type_ == "basket":
            return int(await self.bot.db.fetchval("UPDATE economy SET basket = $2 WHERE user_id = $1 RETURNING basket", user_id, str(amount + basket)))
        else:
            return int(await self.bot.db.fetchval("UPDATE economy SET bank = $2 WHERE user_id = $1 RETURNING bank", user_id, str(amount + bank)))
    
    @commands.command(aliases=["bal"])
    async def balance(self, ctx):
        basket, bank = await self.get_balance(ctx.author.id)
        embed = discord.Embed(color=self.bot.color, title=f"{ctx.author.name}'s balance")
        embed.add_field(name=f"{BOBO} Basket", value=basket, inline=False)
        embed.add_field(name=f"{BOBO} Bank", value=bank, inline=False)
        await ctx.send(embed=embed)
    
    @commands.command(aliases=["with", "wd"])
    async def withdraw(self, ctx, amount: str):
        basket, bank = await self.get_balance(ctx.author.id)
        if amount in ["max", "all"]:
            await self.change_balance(ctx.author.id, -1 * bank, "bank")
            changed_balance = await self.change_balance(ctx.author.id, bank, "basket")
            return await ctx.send(f"Withdrawed {BOBO} {bank} bobo to basket.")
        try:
            amount = int(amount)
        except:
            try:
                amount = int(float(amount))
            except:
                return await ctx.send("Invalid amount")
        if amount > basket:
            return await ctx.send("You don't have that much bobo.")
        if amount <= 0:
            return await ctx.send("You can't withdraw 0 or negative bobo.")
        await ctx.send(f"Withdrawed {BOBO} {amount} bobo to basket.")

    @commands.command(aliases=["dep"])
    async def deposit(self, ctx, amount: str):
        basket, bank = await self.get_balance(ctx.author.id)
        if amount in ["max", "all"]:
            await self.change_balance(ctx.author.id, -1 * basket)
            changed_balance = await self.change_balance(ctx.author.id, basket, "bank")
            return await ctx.send(f"Deposited {BOBO} {basket} bobo to bank.")
        try:
            amount = int(amount)
        except:
            try:
                amount = int(float(amount))
            except:
                return await ctx.send("Invalid amount")
        if amount > basket:
            return await ctx.send("You don't have that much bobo.")
        if amount <= 0:
            return await ctx.send("You can't deposit 0 or negative bobo.")
        await ctx.send(f"Deposited {BOBO} {amount} bobo to bank.")
    
    @commands.is_owner()
    @commands.command()
    async def addmoney(self, ctx, member: discord.Member, amount: int):
        await self.open_account(member.id)
        changed_balance = await self.change_balance(member.id, amount)
        await ctx.send(f"Changed {str(member)}'s balance to {changed_balance}")

def setup(bot):
    bot.add_cog(Currency(bot))
