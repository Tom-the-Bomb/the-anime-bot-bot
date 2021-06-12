import asyncio
import datetime

import discord
import humanize
from dateparser.search import search_dates
from discord.ext import commands


class Timer:
    __slots__ = ("id", "user_id", "time", "reason", "message_jump", "channel_id")

    def __init__(self, record):
        self.id = record["id"]
        self.user_id = record["user_id"]
        self.time = record["time"]
        self.reason = record["reason"]
        self.message_jump = record["message_jump"]
        self.channel_id = record["channel_id"]


class Reminder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(
            asyncio.to_thread(
                search_dates,
                "in 10 seconds",
                settings={"TIMEZONE": "UTC", "PREFER_DATES_FROM": "future", "FUZZY": True},
            )
        )
        self.waiting_tasks = []
        self.already_waiting = []
        self.bot.loop.create_task(self.get_reminders())

    #     self.get_reminders_task = self.bot.loop.create_task(self.get_reminders())

    # def cog_unload(self):
    #     self.get_reminders_task.cancel()

    def cog_unload(self):
        for i in self.waiting_tasks:
            i.cancel()

    @commands.Cog.listener()
    async def on_timer_complete(self, timer):
        channel = self.bot.get_channel(timer.channel_id)
        if channel:
            try:
                await channel.send(
                    f"<@{timer.user_id}>: {discord.utils.escape_mentions(timer.reason)}\n{timer.message_jump}",
                    allowed_mentions=discord.AllowedMentions(
                        everyone=False, users=True, roles=False, replied_user=False
                    ),
                )
            except:
                pass

    async def wait_for_timers(self, timer):
        if timer.time > datetime.datetime.utcnow():
            await asyncio.sleep((timer.time - datetime.datetime.utcnow()).total_seconds())
            self.bot.dispatch("timer_complete", timer)
        await self.bot.db.execute("DELETE FROM reminder WHERE id = $1", timer.id)
        del self.already_waiting[timer.id]
        self.bot.loop.create_task(self.get_reminders())

    async def get_reminders(self):
        await self.bot.wait_until_ready()
        e = await self.bot.db.fetchrow("SELECT * FROM reminder ORDER BY time ASC LIMIT 1")
        if e and e["id"] not in self.already_waiting:
            self.waiting_tasks.append(self.bot.loop.create_task(self.wait_for_timers(Timer(e))))
            self.already_waiting.append(e["id"])
            await asyncio.sleep(0)

    async def create_reminder(self, time, reason, user, message):
        id = await self.bot.db.fetchrow(
            "INSERT INTO reminder (user_id, time, reason, message_jump, channel_id) VALUES ($1, $2, $3, $4, $5) RETURNING id",
            user.id,
            time,
            reason,
            message.jump_url,
            message.channel.id,
        )
        return id["id"]

    @commands.group()
    async def remind(self, ctx, *, arg: str):
        parsed = search_dates(
            arg,
            settings={"TIMEZONE": "UTC", "PREFER_DATES_FROM": "future", "FUZZY": True},
        )
        if not parsed:
            return await ctx.send("hmm idk what you mean do something like remind me in 13 seconds hm idk")
        string_date = parsed[0][0]
        date_obj = parsed[0][1]
        if date_obj <= datetime.datetime.utcnow():
            return await ctx.send("I don't have a time traveler to remind you at the past")
        reason = arg.replace(string_date, "")
        if reason[0:2] == "me" and reason[0:6] in ("me to ", "me in ", "me at "):
            reason = reason[6:]
        id = await self.create_reminder(date_obj, reason, ctx.author, ctx.message)
        await ctx.send(
            f"Ok, {ctx.author.mention} in {humanize.precisedelta(date_obj - datetime.datetime.utcnow())} {reason} (ID: {id})",
            allowed_mentions=discord.AllowedMentions(everyone=False, users=True, roles=False, replied_user=False),
        )
        self.bot.loop.create_task(self.get_reminders())

    # @remind.command()
    # async def cancel(self, ctx, id:int):
    #     try:
    #         await self.bot.db.execute("DELETE FROM reminder WHERE user_id = $1, id = $2", ctx.author.id, id)
    #     except:


def setup(bot):
    bot.add_cog(Reminder(bot))
