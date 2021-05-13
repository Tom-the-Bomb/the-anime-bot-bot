import ujson
import asyncpg
import random

import discord
from discord.ext import commands

BOBO = "\U0000232C"


class Economy(commands.Cog):
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
        return int(bal["basket"]), int(bal["bank"])

    async def change_balance(self, user_id, amount, type_="basket"):
        await self.open_account(user_id)
        basket, bank = await self.get_balance(user_id)
        total_earned = await self.bot.db.fetchval("SELECT total_earned FROM economy WHERE user_id = $1", user_id)
        if amount > 0:
            await self.bot.db.execute("UPDATE economy SET total_earned = $2 WHERE user_id = $1", user_id, int(total_earned) + int(amount))
        if type_ == "basket":
            return int(await self.bot.db.fetchval("UPDATE economy SET basket = $2 WHERE user_id = $1 RETURNING basket", user_id, int(amount) + int(basket)))
        else:
            return int(await self.bot.db.fetchval("UPDATE economy SET bank = $2 WHERE user_id = $1 RETURNING bank", user_id, int(amount) + int(bank)))
    
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
        if amount > bank:
            return await ctx.send("You don't have that much bobo.")
        if amount <= 0:
            return await ctx.send("You can't withdraw 0 or negative bobo.")
        await self.change_balance(ctx.author.id, -1 * amount, "bank")
        await self.change_balance(ctx.author.id, amount)
        await ctx.send(f"Withdrawed {BOBO} {amount} bobo to basket.")

    @commands.command()
    async def lb(self, ctx):
        e = await self.bot.db.fetch("SELECT * FROM economy ORDER BY basket DESC LIMIT 10")
        to_sort = []
        # for i in e:
        #     basket, bank = int(i["basket"]), int(i["bank"])
        #     u = await self.bot.getch(i["user_id"])
        #     to_sort.append(f"{basket + bank} - {str(u)}")
        # def sortlist(e):
        #     return e.split("-")[0]
        # to_sort.sort(key=sortlist)
        # final_sorted = "\n".join(to_sort)
        for i in e:
            to_sort.append(f"{i['basket']} - {str(await self.bot.getch(i['user_id']))}")
        final_sorted = "\n".join(to_sort)
        await ctx.send(embed=discord.Embed(color=self.bot.color, title="Global economy leaderboard", description=final_sorted).set_footer(text="Top 10 global leaderboard, this is wallet not total."))

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
        await self.change_balance(ctx.author.id, -1 * amount)
        await self.change_balance(ctx.author.id, amount, "bank")
        await ctx.send(f"Deposited {BOBO} {amount} bobo to bank.")
    
    @commands.command()
    async def beg(self, ctx):
        characters = [
            "Tanjiro Kamado",
            "Nezuko Kamado",
            "Zenitsu Agatsuma",
            "Inosuke Hashibira",
            "Kanao Tsuyuri",
            "Kagaya Ubuyashiki",
            "Amane Ubuyashiki",
            "Hinaki Ubuyashiki",
            "Nichika Ubuyashiki",
            "Kiriya Ubuyashiki",
            "Kanata Ubuyashiki",
            "Kuina Ubuyashiki",
            "Giyū Tomioka",
            "Shinobu Kochō",
            "Kyōjurō Rengoku",
            "Tengen Uzui",
            "Mitsuri Kanroji",
            "Muichirō Tokitō",
            "Gyōmei Himejima",
            "Obanai Iguro",
            "Sanemi Shinazugawa",
            "Aoi Kanzaki",
            "Goto",
            "Sumi Nakahara",
            "Hotaru Haganezuka",
            "Kozo Kanamori",
            "Kotetsu",
            "Murata",
            "Ozaki",
            "Kanae Kocho",
        ]
        rand = random.randint(-1, 1000)
        if rand <= 0:
            await self.change_balance(ctx.author.id, -1)
            return await ctx.send(f"smh Muzan Kibutsuji almost killed you and take away {BOBO} 1 bobo")
        await self.change_balance(ctx.author.id, rand)
        await ctx.send(f"{random.choice(characters)} just gave you {BOBO} {rand} bobo")
    @commands.is_owner()
    @commands.command()
    async def addmoney(self, ctx, member: discord.Member, amount: int):
        await self.open_account(member.id)
        changed_balance = await self.change_balance(member.id, amount)
        await ctx.send(f"Changed {str(member)}'s balance to {changed_balance}")

def setup(bot):
    bot.add_cog(Economy(bot))
