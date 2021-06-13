from typing import Union

import discord
from discord.ext import commands, menus
from utils.fuzzy import finder
from utils.subclasses import AnimeContext


class RecentBansSource(menus.AsyncIteratorPageSource):
    def __init__(self, entity):
        super().__init__(entity, per_page=1)

    async def format_page(self, menu, entries):
        embed = discord.Embed(color=menu.bot.color, timestamp=entries.created_at)
        embed.set_author(name=str(entries.user), icon_url=str(entries.user.avatar_url_as(static_format="png")))
        embed.set_thumbnail(url=str(entries.target.avatar_url_as(static_format="png")))
        embed.add_field(name="Target banned", value=f"{str(entries.target)} ({entries.target.id})", inline=False)
        embed.add_field(name="Banned by", value=f"{str(entries.user)} ({entries.user.id})", inline=False)
        embed.add_field(name="Reason", value=entries.reason, inline=False)
        return {"embed": embed}


class BannedMember(commands.Converter):
    async def convert(self, ctx, argument):
        entity = None
        if argument.isdigit():
            try:
                member_id = int(argument)
                try:
                    entity = await ctx.guild.fetch_ban(member_id)
                except discord.NotFound:
                    raise commands.BadArgument("That member was not banned before.")
            except ValueError:
                pass
        ban_list = await ctx.guild.bans()
        if not entity:
            entity = discord.utils.find(lambda u: str(u.user) == argument, ban_list)
        if not entity:
            entity = discord.utils.find(lambda u: str(u.user.name) == argument, ban_list)
        if not entity:
            raise commands.BadArgument("That member was not banned before.")
        return entity.user.id


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
    # async def unmute(self, ctx: AnimeContext, user: discord.Member, *, reason=None):# noqa: E501
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
    # async def mute(self, ctx: AnimeContext, user: discord.Member, *, reason=None):# noqa: E501
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

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def nuke(self, ctx, reason: str = None):
        c = await ctx.channel.clone(reason=f"Channel nuked by {ctx.author} ({ctx.author.id}) Reason: {reason}")
        await ctx.channel.delete(reason=f"Channel nuked by {ctx.author} ({ctx.author.id}) Reason: {reason}")
        await c.send(f"Channel nuked by {ctx.author} ({ctx.author.id}) Reason: {reason}")

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def slowmode(self, ctx, seconds: int = 0):
        if seconds > 21600:
            return await ctx.send("Seconds could not be greater then 21600")
        elif seconds < 0:
            return await ctx.send("Seconds could not be less then 0")
        await ctx.channel.edit(slowmode_delay=seconds, reason=f"Slowmode edited by {ctx.author} ({ctx.author.id})")
        await ctx.send(f"Edited slowmode to {seconds}")

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True, manage_channels=True)
    async def mutesetup(self, ctx):
        r = discord.utils.find(lambda x: x.name == "Muted", ctx.guild.roles)
        if not r:
            return await ctx.send(
                "Please create a role named: `Muted` case sensitive, and make sure to drag it above the member's role."
            )
        for c in ctx.guild.channels:
            o = c.overwrites
            if role_overwrite := o.get(r):
                if role_overwrite.send_messages is False and role_overwrite.connect is False and role_overwrite.add_reactions is False:
                    continue
            o[r] = discord.PermissionOverwrite(send_messages=False, connect=False, add_reactions=False)
            await c.edit(overwrites=o, reason="Muted role")
        await ctx.send("Done.")

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def mute(self, ctx, members: commands.Greedy[discord.Member]):
        if not members:
            return await ctx.send("User not found.")
        for member in members:
            if member.top_role >= ctx.author.top_role:
                return await ctx.send(f"{member.mention} have a higher role then you, you can not do that.")
            r = discord.utils.find(lambda x: x.name == "Muted", ctx.guild.roles)
            if not r:
                return await ctx.send(f"Muted role is not found, run {ctx.prefix}mutesetup to setup mute.")
            await member.add_roles(r, reason=f"Muted by: {ctx.author} ({ctx.author.id})")
        await ctx.reply(f"Muted {', '.join((i.mention for i in members))}")

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def unmute(self, ctx, members: commands.Greedy[discord.Member]):
        if not members:
            return await ctx.send("User not found.")
        for member in members:
            if member.top_role >= ctx.author.top_role:
                return await ctx.send(f"{member.mention} have a higher role then you, you can not do that.")
            r = discord.utils.find(lambda x: x.name == "Muted", ctx.guild.roles)
            if not r:
                return await ctx.send(f"Muted role is not found, run {ctx.prefix}mutesetup to setup mute.")
            await member.remove_roles(r, reason=f"Unmuted by: {ctx.author} ({ctx.author.id})")
        await ctx.reply(f"Unmuted {', '.join((i.mention for i in members))}")

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(view_audit_log=True)
    async def recentbans(self, ctx, limit: int = 100):
        pages = menus.MenuPages(
            source=RecentBansSource(ctx.guild.audit_logs(limit=limit, action=discord.AuditLogAction.ban)),
            delete_message_after=True,
        )
        await pages.start(ctx)

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def badword(self, ctx):
        if ctx.guild.id not in self.bot.bad_word_cache.keys():
            return await ctx.send("logging is not enabled")
        await ctx.author.send(", ".join(self.bot.bad_word_cache[ctx.guild.id]))
        await ctx.send("I have dmed you the list of bad words of this server")

    @badword.command()
    @commands.guild_only()
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
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def warn(self, ctx: AnimeContext, user: discord.Member, *, reason):
        if user.id == 590323594744168494:
            return await ctx.send("nope")
        if user.top_role >= ctx.author.top_role:
            return await ctx.send(f"{user.mention} have a higher role then you, you can not do that.")
        embed = discord.Embed(color=self.bot.color)
        embed.add_field(name=f"`{user}` have been warned", value=f"with reason: `{reason}`")
        await ctx.send(embed=embed)
        embed = discord.Embed(color=self.bot.color)
        embed.add_field(name="You have been warned", value=f"with reason: `{reason}`")
        await user.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def purge(self, ctx: AnimeContext, limit: int):
        counts = await ctx.channel.purge(limit=limit)
        await ctx.send(content=f"Purged {len(counts)} messages", delete_after=10)

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    async def kick(self, ctx: AnimeContext, members: commands.Greedy[discord.Member], *, reason=None):
        if not members:
            return await ctx.send("User not found.")
        for member in members:
            if member.id == 590323594744168494:
                return await ctx.reply("hmm nope not gonna do that")
            if ctx.author.top_role < member.top_role:
                return await ctx.reply(f"Your role is lower then {member}")
            await member.kick(reason=f"Kicked by {ctx.author} ({ctx.author.id}) Reason: {reason}")
        await ctx.reply(f"Kicked {', '.join((i.mention for i in members))}")

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def softban(self, ctx: AnimeContext, members: commands.Greedy[discord.Member], *, reason=None):
        if not members:
            return await ctx.send("User not found.")
        for member in members:
            if member.id == 590323594744168494:
                return await ctx.reply("hmm nope not gonna do that")
            if ctx.author.top_role < member.top_role:
                return await ctx.reply(f"Your role is lower then {member}")
            await member.ban(
                reason=f"Soft banned by {ctx.author} ({ctx.author.id}) Reason: {reason}", delete_message_days=7
            )
            await member.unban(reason=f"Soft banned by {ctx.author} ({ctx.author.id}) Reason: {reason}")
        await ctx.reply(f"Soft banned {', '.join((i.mention for i in members))}")

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def ban(
        self, ctx: AnimeContext, members: commands.Greedy[Union[discord.Member, discord.User]], *, reason=None
    ):
        if not members:
            return await ctx.send("User not found.")
        for member in members:
            if member.id == 590323594744168494:
                return await ctx.reply("hmm nope not gonna do that")
            if isinstance(member, discord.Member) and ctx.author.top_role < member.top_role:
                return await ctx.reply(f"Your role is lower then {member}")
            await ctx.guild.ban(
                member, reason=f"Banned by {ctx.author} ({ctx.author.id}) Reason: {reason}", delete_message_days=7
            )
        await ctx.reply(f"Banned {', '.join((i.mention for i in members))}")

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def rawunban(self, ctx: AnimeContext, members: commands.Greedy[int]):
        """
        Useful when you have a bunch of user ids to unban
        """
        if not members:
            return await ctx.send("User not found.")
        for member in members:
            member = discord.Object(id=member)
            await ctx.guild.unban(member, reason=f"{ctx.author} ({ctx.author.id}) unbanned")
        await ctx.send(f"Unbanned: {', '.join((str(i) for i in members))}")

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def unban(self, ctx: AnimeContext, *, member: BannedMember):
        member = discord.Object(id=member)
        await ctx.guild.unban(member, reason=f"{ctx.author} ({ctx.author.id}) unbanned")
        await ctx.send(f"Unbanned {member.id}")


def setup(bot):
    bot.add_cog(Moderations(bot))
