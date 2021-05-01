import discord
from discord.ext import commands
from dateparser.search import search_dates
import humanize

class Reminder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def create_reminder(self, time, reason, user, message):
        await self.bot.db.execute("INSERT INTO reminder VALUES ($1, $2, $3, $4)", user.id, time, reason, message.jump_url)


    
    @commands.command()
    async def remind(self, ctx, *, arg: str):
        parsed = search_dates(arg)
        if not parsed:
            return await ctx.send("hmm idk what you mean do something like do stuff at 10 minutes later")
        string_date = parsed[0][0]
        date_obj = parsed[0][1]
        if date_obj.tzinfo:
            date_obj = date_obj + date_obj.tzinfo.utcoffset(date_obj)
        if date_obj <= ctx.message.created_at:
            return await ctx.send("I don't have a time traveler to remind you at the past")
        await self.create_reminder(date_obj, reason, ctx.author, ctx.message)
        await ctx.send(f"Ok, {ctx.author.mention} in {humanize.precisedelta(date_obj)} {reason}")
        