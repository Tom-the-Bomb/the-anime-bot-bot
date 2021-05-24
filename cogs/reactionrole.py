import discord
import ujson
from discord.ext import commands
from utils.subclasses import AnimeContext
import typing
import ratelimiter


class ReactionRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.reactionrole_cache = {}
        self.ratelimiter = ratelimiter.RateLimiter(max_calls=5, period=10)
        self.bot.loop.create_task(self.make_cache())

    async def make_cache(self):
        roles = await self.bot.db.fetch("SELECT * FROM reactionrole")
        if roles:
            for i in roles:
                self.bot.reactionrole_cache[i["guild_id"]] = ujson.loads(i["roles"])


    @commands.group()
    async def reactionrole(self, ctx):
        ...

    @reactionrole.command()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def add(self, ctx: AnimeContext):
        reaction = await ctx.send("hi react reaction to this message")
        r = await self.bot.wait_for(
            "raw_reaction_add",
            check=lambda x: x.message_id == reaction.id and x.user_id == ctx.author.id,
            timeout=60,
        )
        try:
            m = await ctx.send("testing emoji")
            await m.add_reaction(r.emoji)
            await m.delete()
        except:
            await ctx.send("either i can't use the emoji or i can't react to it")
        await ctx.send("ok what role?")
        role = await self.bot.wait_for(
            "message",
            check=lambda x: x.channel.id == ctx.channel.id and x.author.id == ctx.author.id,
        )
        role = await commands.RoleConverter().convert(ctx, role.content)
        if not role:
            await ctx.send("invalid role")
        await ctx.send("ok what channel")
        c = await self.bot.wait_for(
            "message",
            check=lambda x: x.channel.id == ctx.channel.id and x.author.id == ctx.author.id,
        )
        c = await commands.TextChannelConverter().convert(ctx, c.content)
        await ctx.send("ok what message")
        m = await self.bot.wait_for(
            "message",
            check=lambda x: x.channel.id == ctx.channel.id and x.author.id == ctx.author.id,
        )
        m = await c.fetch_message(m.content)
        await m.add_reaction(r.emoji)
        await ctx.send("oh ok made")
        if not self.bot.reactionrole_cache.get(ctx.guild.id):
            self.bot.reactionrole_cache[ctx.guild.id] = {}
        if not self.bot.reactionrole_cache.get(ctx.guild.id).get(m.id):
            self.bot.reactionrole_cache[ctx.guild.id][m.id] = {}
        self.bot.reactionrole_cache[ctx.guild.id][m.id][r.emoji.id] = role.id or role.name
        await self.bot.db.execute(
            "INSERT INTO reactionrole VALUES ($1, $2) ON CONFLICT (guild_id) DO UPDATE SET roles = $2",
            ctx.guild.id,
            ujson.dumps(self.bot.reactionrole_cache[ctx.guild.id]),
        )

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Gives a role based on a reaction emoji."""
        # Make sure that the message the user is reacting to is the one we care about
        if not payload.guild_id:
            return
        if payload.guild_id not in self.bot.reactionrole_cache.keys():
            return
        try:
            role_id = self.bot.reactionrole_cache[payload.guild_id][str(payload.message_id)][
                str(payload.emoji.id) or payload.emoji.name
            ]
        except KeyError:
            # If the emoji isn't the one we care about then exit as well.
            return
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            # Check if we're still in the guild and it's cached.
            return
        role = guild.get_role(role_id)
        if role is None:
            # Make sure the role still exists and is valid.
            return
        try:
            # Finally add the role
            async with self.ratelimiter:
                await payload.member.add_roles(role, reason="The Anime Bot reaction role")
        except discord.HTTPException:
            # If we want to do something in case of errors we'd do it here.
            pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        """Removes a role based on a reaction emoji."""
        # Make sure that the message the user is reacting to is the one we care about
        if not payload.guild_id:
            return
        if payload.guild_id not in self.bot.reactionrole_cache.keys():
            return
        try:
            role_id = self.bot.reactionrole_cache[payload.guild_id][str(payload.message_id)][
                str(payload.emoji.id) or payload.emoji.name
            ]
        except KeyError:
            # If the emoji isn't the one we care about then exit as well.
            return
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            # Check if we're still in the guild and it's cached.
            return
        role = guild.get_role(role_id)
        if role is None:
            # Make sure the role still exists and is valid.
            return
        member = guild.get_member(payload.user_id)
        if member is None:
            # Makes sure the member still exists and is valid
            return
        try:
            # Finally, remove the role
            async with self.ratelimiter:
                await member.remove_roles(role, reason="The Anime Bot reaction role")
        except discord.HTTPException:
            # If we want to do something in case of errors we'd do it here.
            pass


def setup(bot):
    bot.add_cog(ReactionRole(bot))
