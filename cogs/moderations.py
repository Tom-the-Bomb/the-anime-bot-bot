import discord
from discord.ext import commands
from utils.subclasses import AnimeContext
from utils.fuzzy import finder


class Moderations(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.build_cache())

    async def build_cache(self):
        await self.bot.wait_until_ready()
        bad_words = await self.bot.db.fetch("SELECT * FROM bad_words")
        if not bad_words:
            return
        for i in bad_words:
            self.bot.bad_word_cache[i["guild_id"]] = i["words"]

    # @commands.command()
    # @commands.has_permissions(manage_messages=True)
    # @commands.bot_has_permissions(manage_roles=True)
    # async def unmute(self, ctx: AnimeContext, user: discord.Member, *, reason="None"):# noqa: E501
    #   if finder("Muted", user.roles, key=lambda t: t.name, lazy=False)[:3] == []:# noqa: E501
    #     return await ctx.send("user not muted")
    #   role = finder("Muted", user.roles, key=lambda t: t.name, lazy=False)[0]
    #   await user.remove_roles(role, reason=f"{ctx.author}: {reason} ({ctx.author.id})")# noqa: E501
    #   embed = discord.Embed(color=self.bot.color)
    #   embed.add_field(name=f"`{user}` have been unmuted", value=f"with reason: `{reason}`")# noqa: E501
    #   return await ctx.send(embed=embed)
    # @commands.command()
    # @commands.has_permissions(manage_messages=True)
    # @commands.bot_has_permissions(manage_roles=True)
    # async def mute(self, ctx: AnimeContext, user: discord.Member, *, reason="None"):# noqa: E501
    #   permissions=discord.Permissions.text()
    #   permissions.send_messages=False
    #   if finder("Muted", user.roles, key=lambda t: t.name, lazy=False)[:3] != []:# noqa: E501
    #     return await ctx.send("user already muted")
    #   if finder("Muted", ctx.guild.roles, key=lambda t: t.name, lazy=False)[:3] == []:# noqa: E501
    #     role = await ctx.guild.create_role(name="Muted", permissions=permissions, reason="Muted role")# noqa: E501
    #     await user.add_roles(role, reason=f"{ctx.author}: {reason} ({ctx.author.id})")# noqa: E501
    #     embed = discord.Embed(color=self.bot.color)
    #     embed.add_field(name=f"`{user}` have been muted", value=f"with reason: `{reason}`")# noqa: E501
    #     return await ctx.send(embed=embed)
    #   else:
    #     role = finder("Muted", ctx.guild.roles, key=lambda t: t.name, lazy=False)[0]# noqa: E501
    #     if role.permissions != permissions:
    #       await role.edit(permissions=permissions)
    #     await user.add_roles(role, reason=f"{ctx.author}: {reason} ({ctx.author.id})")# noqa: E501
    #     embed = discord.Embed(color=self.bot.color)
    #     embed.add_field(name=f"`{user}` have been muted", value=f"with reason: `{reason}`")# noqa: E501
    #     return await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload):
        if not payload.data.get("guild_id"):
            return
        if payload.data.get("guild_id") not in self.bot.bad_word_cache.keys():
            return
        bad_words = self.bot.bad_word_cache[payload.data.get("guild_id")]
        if not payload.data.get("content"):
            return
        for i in bad_words:
            if i.lower() in payload.data.get("content"):
                try:
                    await self.bot.http.delete_message(
                        payload.data.get("channel_id"),
                        payload.data.get("id"),
                        reason="Bad word detected",
                    )
                except:
                    pass

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild:
            return
        if message.guild.id not in self.bot.bad_word_cache.keys():
            return
        bad_words = self.bot.bad_word_cache[message.guild.id]
        for i in bad_words:
            if i.lower() in message.content.lower():
                try:
                    await self.bot.http.delete_message(
                        message.channel.id,
                        message.id,
                        reason="Bad word detected",
                    )
                except:
                    pass

    @commands.group(invoke_without_command=True)
    @commands.has_permissions(manage_messages=True)
    async def badword(self, ctx):
        if ctx.guild.id not in self.bot.bad_word_cache.keys():
            return await ctx.send("logging is not enabled")
        await ctx.author.send(", ".join(self.bot.bad_word_cache[ctx.guild.id]))
        await ctx.send("I have dmed you the list of bad words of this server")

    @badword.command()
    @commands.has_permissions(manage_messages=True)
    async def add(self, ctx: AnimeContext, *, word):
        if ctx.guild.id not in self.bot.bad_word_cache.keys():
            self.bot.bad_word_cache[ctx.guild.id] = [word]
            await self.bot.db.execute(
                "INSERT INTO bad_words VALUES ($1, $2)",
                ctx.guild.id,
                self.bot.bad_word_cache[ctx.guild.id],
            )
        else:
            if word in self.bot.bad_word_cache[ctx.guild.id]:
                return await ctx.send("already in bad word list")
            old_bad_words = self.bot.bad_word_cache[ctx.guild.id]
            old_bad_words.append(word)
            await self.bot.db.execute(
                "UPDATE bad_words SET words = $2 WHERE guild_id = $1",
                ctx.guild.id,
                self.bot.bad_word_cache[ctx.guild.id],
            )
        await ctx.message.delete()
        await ctx.send("Success", delete_after=5)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def warn(self, ctx: AnimeContext, user: discord.Member, *, reason):
        if user.id == 590323594744168494:
            return await ctx.send("nope")
        embed = discord.Embed(color=self.bot.color)
        embed.add_field(name=f"`{user}` have been warned", value=f"with reason: `{reason}`")
        await ctx.send(embed=embed)
        embed = discord.Embed(color=self.bot.color)
        embed.add_field(name=f"You have been warned", value=f"with reason: `{reason}`")
        await user.send(embed=embed)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def purge(self, ctx: AnimeContext, limit: int):
        await ctx.trigger_typing()
        counts = await ctx.channel.purge(limit=limit)
        await ctx.send(content=f" purged {len(counts)} messages", delete_after=10)

    @commands.command()
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    async def kick(self, ctx: AnimeContext, member: discord.Member, *, reason=None):
        if member.id == 590323594744168494:
            return await ctx.reply("hmm nope not gonna do that")
        if ctx.author.top_role < member.top_role:
            return await ctx.reply(f"Your role is lower then {member}")
        await ctx.trigger_typing()
        await member.kick(reason=reason)
        await ctx.reply(f"Kicked {member}")

    @commands.command()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def ban(self, ctx: AnimeContext, member: discord.Member, *, reason=None):
        if member.id == 590323594744168494:
            return await ctx.reply("hmm nope not gonna do that")
        if ctx.author.top_role < member.top_role:
            return await ctx.reply(f"Your role is lower then {member}")
        await ctx.trigger_typing()
        await member.ban(reason=reason)
        await ctx.reply(f"banned {member}")

    @commands.command()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def unban(self, ctx: AnimeContext, *, member):
        await ctx.trigger_typing()
        member = discord.Object(id=member.id)
        try:
            await member.unban(reason=f"{ctx.author.id}: unbanned")
        except:
            await ctx.send("can not unban")


def setup(bot):
    bot.add_cog(Moderations(bot))
