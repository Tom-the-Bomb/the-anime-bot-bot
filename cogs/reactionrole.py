import discord
import orjson
from discord.ext import commands
from utils.subclasses import AnimeContext
import typing
import ratelimiter


class reactionrole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.reactionrole_cache = {}
        self.ratelimiter = ratelimiter.RateLimiter(max_calls=5, period=10)
        self.bot.loop.create_task(self.make_cache())

    async def make_cache(self):
        roles = await self.bot.db.fetch("SELCT * FROM reactionrole")
        if roles:
            for i in roles:
                self.bot.reactionrole_cache[i["guild_id"]] = {}
                self.bot.reactionrole_cache[i["guild_id"]] = orjson.loads(
                    i["roles"]
                )

    @commands.group()
    async def reactionrole(self, ctx):
        ...

    @reactionrole.command()
    async def add(
        self,
        ctx: AnimeContext,
        role: discord.Role,
        message_id: int,
        reaction: typing.Union[discord.Emoji, discord.PartialEmoji, str],
    ):
        """
        Reaction Role is currently in beta so bugs are expected
        Adding a existing reaction role message will override it
        For guide on how to find message id
        https://support.discord.com/hc/en-us/articles/206346498-Where-can-I-find-my-User-Server-Message-ID-
        Usage:
        ovo reactionrole add (@rolename or role id) messageid reaction
        ovo reactionrole add @humans 928328288232222 :rooHi:
        """
        if isinstance(reaction, (discord.Emoji, discord.PartialEmoji)):
            emoji = reaction.id
        else:
            try:
                await ctx.message.add_reaction(reaction)
                emoji = reaction
            except:
                return await ctx.send("Invalid Emoji")
        if not self.bot.reactionrole_cache.get(ctx.guild.id):
            self.bot.reactionrole_cache[ctx.guild.id] = {}
            self.bot.reactionrole_cache[ctx.guild.id][message_id] = {
                emoji: role.id
            }
        else:
            self.bot.reactionrole_cache[ctx.guild.id][message_id][
                emoji
            ] = role.id
        await self.bot.db.execute(
            "INSERT INTO reactionrole VALUES ($1, $2) ON CONFLICT DO UPDATE SET roles = $2",
            ctx.guild.id,
            orjson.dumps(self.bot.reactionrole_cache[ctx.guild.id][message_id]),
        )
        await ctx.send(
            f"Sucess role is {role.mention}, message id is {message_id}, reaction is {str(reaction)}"
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
            role_id = self.bot.reactionrole_cache[payload.guild_id][
                payload.message_id
            ][payload.emoji.id or payload.emoji.name]
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
                await payload.member.add_roles(
                    role, reason="The Anime Bot reaction role"
                )
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
            role_id = self.bot.reactionrole_cache[payload.guild_id][
                payload.message_id
            ][payload.emoji.id or payload.emoji.name]
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
                await member.remove_roles(
                    role, reason="The Anime Bot reaction role"
                )
        except discord.HTTPException:
            # If we want to do something in case of errors we'd do it here.
            pass


def setup(bot):
    bot.add_cog(reactionrole(bot))
