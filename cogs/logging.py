import discord
from discord.ext import commands
import humanize
import datetime

class logging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.make_cache())

    async def make_cache(self):
        logs = await self.bot.db.fetch("SELECT * FROM logging")
        if logs:
            for i in logs:
                self.bot.logging_cache[i["guild_id"]] = dict(i.items())

    @commands.group(invoke_without_command=True)
    async def logging(self, ctx):
        """
        View the status of logging
        """
        logging_settings = self.bot.logging_cache.get(ctx.guild.id)
        if not logging_settings:
            return await ctx.send(f"You have not enable logging run {ctx.prefix}logging setup to enable it")
        settings = [f"{i} - {v}" for i,v in logging_settings.items()]
        settings = "\n".join(settings)
        await ctx.send(embed=discord.Embed(color=self.bot.color, description=settings))
    @logging.command()
    async def setup(self, ctx, channel:discord.TextChannel):
        """
        Setup logging:
        Usage:
        ovo logging setup #logging
        """
        if ctx.guild.id not in self.bot.logging_cache.keys():
            try:
                webhook = await channel.create_webhook(name="The Anime Bot logging", avatar=await self.bot.user.avatar_url_as(format="png").read(), reason="The Anime Bot logging")
            except discord.HTTPException:
                if await channel.webhooks():
                    webhook = random.choice(await channel.webhooks())
                else:
                    return await ctx.send("Unable to create webhook in this channel maybe try a different channel?")
            except discord.Forbidden:
                return await ctx.send("I do not have permission to create webhook in that channel, please make sure I have `manage_webhook` permission")
            logging = await self.bot.db.fetchrow("INSERT INTO logging (guild_id, channel_id, webhook, channel_create, channel_update, channel_delete, role_create, role_update, role_delete, guild_update, emojis_update, member_update, member_ban, member_unban, invite_change, member_join, member_leave, voice_channel_change, message_delete, message_edit) VALUES ($1, $2, $3, $4, $4, $4, $4, $4, $4, $4, $4, $4, $4, $4, $4, $4, $4, $4, $4, $4) RETURNING *;", ctx.guild.id, channel.id, webhook.url, True)
            self.bot.logging_cache[ctx.guild.id] = dict(logging.items())
            await ctx.send(f"Success, logging is enabled in this server, logging channel is {channel.mention}")
        else:
            return await ctx.send(f"Logging is already on use {ctx.prefix}logging off to turn it off")
    
    @logging.command()
    async def off(self, ctx):
        if ctx.guild.id not in self.bot.logging_cache.keys():
            return await ctx.send("logging is already off")
        self.bot.logging_cache.pop(ctx.guild.id)
        await self.bot.db.execute("DELETE FROM logging WHERE guild_id = $1", ctx.guild.id)
        await ctx.send("Success logging have been turn off")


    @logging.command()
    async def toggle(self, ctx, event:str):
        """
        Toggle a certain event
        Usage:
        ovo logging toggle message_edit
        """
        if ctx.guild.id not in self.bot.logging_cache.keys():
            return await ctx.send("Logging is not enabled")
        if not self.bot.logging_cache[ctx.guild.id].get(event):
            return await ctx.send("That not a valid event")
        if self.bot.logging_cache[ctx.guild.id][event]:
            self.bot.logging_cache[ctx.guild.id][event] = False
            await self.bot.db.execute("UPDATE logging SET $1 = $2 WHERE guild_id = $3", event, False, ctx.guild.id)
            return await ctx.send(f"{event} has been turn off")
        else:
            self.bot.logging_cache[ctx.guild.id][event] = True
            await self.bot.db.execute("UPDATE logging SET $1 = $2 WHERE guild_id = $3", event, True, ctx.guild.id)
            return await ctx.send(f"{event} has been turn on")



    async def send_webhook(self, guild_id, embed, event):
        if guild_id not in self.bot.logging_cache.keys():
            return
        if self.bot.logging_cache[guild_id][event] == False:
            return
        webhook_url = self.bot.logging_cache[guild_id]["webhook"]
        channel_id = self.bot.logging_cache[guild_id]["channel_id"]
        webhook = discord.Webhook.from_url(webhook_url, adapter=discord.AsyncWebhookAdapter(self.bot.session))
        try:
            message = await webhook.send(embed=embed, username="The Anime Bot logging", avatar_url=str(self.bot.user.avatar_url_as(format="png")))
        except discord.NotFound:
            channel = self.bot.get_channel(channel_id)
            webhooks = await channel.webhooks()
            if not webhooks:
                webhook = await channel.create_webhook(name="The Anime Bot logging", avatar=await self.bot.user.avatar_url_as(format="png").read(), reason="The Anime Bot logging")
                message = await webhook.send(embed=embed, username="The Anime Bot logging", avatar_url=str(self.bot.user.avatar_url_as(format="png")))
                await self.bot.db.execute("UPDATE logging SET webhook = $1, WHERE guild_id = $2", webhook.url, channel.guild.id)
            webhook = random.choice(webhooks)
            message = await webhook.send(embed=embed, username="The Anime Bot logging", avatar_url=str(self.bot.user.avatar_url_as(format="png")))

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        if channel.guild.id not in self.bot.logging_cache.keys():
            return
        embed = discord.Embed(color=self.bot.color, title="New channel created", description=f"**channel name:** {channel.name}\n**Category:** {channel.category}", timestamp=channel.created_at)
        embed.set_footer(text=f"Channel ID: {channel.id}")
        await self.send_webhook(channel.guild.id, embed, "channel_create")
    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        if channel.guild.id not in self.bot.logging_cache.keys():
            return
        embed = discord.Embed(color=self.bot.color, title="Channel Updated", timestamp=channel.created_at)
        embed.set_footer(text=f"Channel ID: {channel.id}")
        return await self.send_webhook(after.guild.id, embed, "channel_update")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        if channel.guild.id not in self.bot.logging_cache.keys():
            return
        embed = discord.Embed(color=self.bot.color, title="Channel Deleted", description=f"**channel name:** {channel.name}\n**Category:** {channel.category}", timestamp=channel.created_at)
        embed.set_footer(text=f"Channel ID: {channel.id}")
        await self.send_webhook(channel.guild.id, embed, "channel_delete")
    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        if role.guild.id not in self.bot.logging_cache.keys():
            return
        embed = discord.Embed(color=self.bot.color, title="Role Created", description=f"**Role name:** {role.name}\n**Color:** {str(channel.color)}", timestamp=channel.created_at)
        embed.set_footer(text=f"Channel ID: {channel.id}")
        await self.send_webhook(role.guild.id, embed, "role_delete")


    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        if before.color != after.color:
            embed = discord.Embed(color=self.bot.color, title="Role Updated", description=f"**Role name:** {after.name}\n**Old Color:** {str(before.color)}\n**New Color:** {str(after.color)}", timestamp=datetime.datetime.utcnow())
            await self.send_webhook(invite.guild.id, embed, "role_update")
        if before.name != after.name:
            embed = discord.Embed(color=self.bot.color, title="Role Updated", description=f"**Old Role Name:** {before.name}\n**New Role Name:** {after.name}", timestamp=datetime.datetime.utcnow())
            await self.send_webhook(invite.guild.id, embed, "role_update")
        if before.permission != after.permission:
            changed_permission = [(i,v) for i,v in dict(after).items() if dict(before)[i] != v]
            to_display = []
            for i,v in changed_permission:
                to_display.append(f"Added permission {i}") if v else to_display.append(f"Removed permission {i}")
            to_display = "\n".join(to_display)
            embed = discord.Embed(color=self.bot.color, title="Role Updated", description=f"**New Permissions:** {to_display}", timestamp=datetime.datetime.utcnow())
            await self.send_webhook(invite.guild.id, embed, "role_update")
    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        if role.guild.id not in self.bot.logging_cache.keys():
            return
        embed = discord.Embed(color=self.bot.color, title="Role Deleted", description=f"**Role name:** {role.name}\n**Color:** {str(channel.color)}", timestamp=channel.created_at)
        embed.set_footer(text=f"Channel ID: {channel.id}")
        await self.send_webhook(role.guild.id, embed, "role_delete")
    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        if before.afk_channel != after.afk_channel:
            embed = discord.Embed(color=self.bot.color, title="Guild Updated", description=f"**Old Afk channel:** {before.afk_channel.mention}*\n*New Afk channel:** {after.afk_channel.mention}", timestamp=datetime.datetime.utcnow())
            return await self.send_webhook(invite.guild.id, embed, "guild_update")
        if before.afk_timeout != after.afk_timeout:
            embed = discord.Embed(color=self.bot.color, title="Guild Updated", description=f"**Old Afk timeout:** {before.afk_timeout}*\n*New Afk timeout:** {after.afk_timeout}", timestamp=datetime.datetime.utcnow())
            return await self.send_webhook(invite.guild.id, embed, "guild_update")
        if before.name != after.name:
            embed = discord.Embed(color=self.bot.color, title="Guild Updated", description=f"**Old Name:** {before.name}*\n*New name:** {after.name}", timestamp=datetime.datetime.utcnow())
            return await self.send_webhook(invite.guild.id, embed, "guild_update")
        embed = discord.Embed(color=self.bot.color, title="Guild Updated", description=f"Something updated but I can't trace what updated", timestamp=datetime.datetime.utcnow())
        await self.send_webhook(invite.guild.id, embed, "guild_update")

    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild, before, after):
        if len(before) < len(after):
            new_emojis = [str(i) for i in after if i not in before]
            embed = discord.Embed(color=self.bot.color, title="New Emojis Added", description=f"{', '.join(new_emojis)}", timestamp=datetime.datetime.utcnow())
            await self.send_webhook(invite.guild.id, embed, "emojis_update")
        else:
            c = [str(i) for i in before if i not in after]
            embed = discord.Embed(color=self.bot.color, title="Emojis Removed", description=f"{', '.join(removed_emojis)}", timestamp=datetime.datetime.utcnow())
            await self.send_webhook(invite.guild.id, embed, "emojis_update")

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.nick and after.nick and before.nick != after.nick:
            embed = discord.Embed(color=self.bot.color, title="Nickname Changed", description=f"", timestamp=datetime.datetime.utcnow())
            await self.send_webhook(invite.guild.id, embed, "member_update")
        if before.roles != after.roles:
            if len(before.roles) < len(after.roles):
                roles = set(before.roles)
                new_roles = [i for i in after.roles not in roles]
                embed = discord.Embed(color=self.bot.color, title="Role Added", description=f"Member: {member.mention}\nRoles: {', '.join(new_roles)}", timestamp=datetime.datetime.utcnow())
                return await self.send_webhook(invite.guild.id, embed, "member_update")
            else:
                roles = set(after.roles)
                removed_roles = [i for i in before.roles not in roles]
                embed = discord.Embed(color=self.bot.color, title="Role Removed", description=f"Member: {member.mention}\nRoles: {', '.join(removed_roles)}", timestamp=datetime.datetime.utcnow())
                return await self.send_webhook(invite.guild.id, embed, "member_update")
    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        embed = discord.Embed(color=self.bot.color, title="Member Banned", description=f"User: {str(user)} {user.mention} ({user.id})", timestamp=datetime.datetime.utcnow())
        await self.send_webhook(invite.guild.id, embed, "member_ban")
    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        embed = discord.Embed(color=self.bot.color, title="Member Unbanned", description=f"User: {str(user)} {user.mention} ({user.id})", timestamp=datetime.datetime.utcnow())
        await self.send_webhook(invite.guild.id, embed, "member_unban")
    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        embed = discord.Embed(color=self.bot.color, title="Invite Deleted", description=f"Invite ID: {invite.id}\nInvite URL: {invite.url}", timestamp=invite.created_at)
        await self.send_webhook(invite.guild.id, embed, "invite_change")
    @commands.Cog.listener()
    async def on_invite_delete(self, invite):
        embed = discord.Embed(color=self.bot.color, title="Invite Created", description=f"Invite ID: {invite.id}\nInvite URL: {invite.url}", timestamp=invite.created_at)
        await self.send_webhook(invite.guild.id, embed, "invite_change")
    @commands.Cog.listener()
    async def on_member_join(self, member):
        embed = discord.Embed(color=self.bot.color, title="Member joined", description=f"{member.mention} just joined. We now have {member.guild.member_count} members. Account Created at: {humanize.precisedelta(member.created_at)} ago", timestamp=datetime.datetime.now())
        embed.set_footer(text=f"ID: {member.id}")
        await self.send_webhook(member.guild.id, embed, "member_join")
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        embed = discord.Embed(color=self.bot.color, title="Member left", description=f"{member.mention} just left. We now have {member.guild.member_count} members. Account Created at: {humanize.precisedelta(member.created_at)} ago", timestamp=datetime.datetime.now())
        embed.set_footer(text=f"ID: {member.id}")
        await self.send_webhook(member.guild.id, embed, "member_leave")
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if not before.channel:
            embed = discord.Embed(color=self.bot.color, title="Joined voice channel", description=f"{member.display_name} joined voice channel {after.channel.mention}")
            await self.send_webhook(member.guild.id, embed, "voice_channel_change")
        if not after.channel:
            embed = discord.Embed(color=self.bot.color, title="Left voice channel", description=f"{member.display_name} left voice channel {before.channel.mention}")
            await self.send_webhook(member.guild.id, embed, "voice_channel_change")
        if before.channel != after.channel:
            embed = discord.Embed(color=self.bot.color, title="Changed voice channel", description=f"{member.display_name} changed voice channel from {before.channel.mention} to {after.channel.mention}")
            await self.send_webhook(member.guild.id, embed, "voice_channel_change")
        
            
    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload):
        if payload.cached_message:
            RETURNING
        if not payload.data.get("guild_id"):
            return
        embed = discord.Embed(color=self.bot.color, title="Message Edited", description=f"The message is too old I can't find the content", timestamp=datetime.datetime.utcnow())
        await self.send_webhook(payload.guild_id, embed, "message_edit")
    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        before_content = before.content or  "message don't have content could be a attachment or embed"
        after_content = after.content or  "message don't have content could be a attachment or embed"
        embed = discord.Embed(color=self.bot.color, title="Message Deleted", timestamp=datetime.datetime.utcnow())
        embed.add_field(name="Before", value=f"**Content:** {before_content}")
        embed.add_field(name="After", value=f"**Content:** {after_content}")
        await self.send_webhook(after.guild.id, embed, "message_edit")
    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload):
        ids = "\n".join(payload.message_ids)
        embed = discord.Embed(color=self.bot.color, title="Bulk messages deleted", description=f"Message Ids: \n{ids}")
        await self.send_webhook(payload.guild_id, embed, "message_delete")
    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):
        if not payload.guild_id:
            return
        if message.webhook_id:
            return
        message = payload.cached_message
        if message:
            content = message.content or  "message don't have content could be a attachment or embed"
            embed = discord.Embed(color=self.bot.color, title="Message Deleted", description=f"**Content:** {content}", timestamp=datetime.datetime.utcnow())
            await self.send_webhook(message.guild.id, embed, "message_delete")
        else:
            embed = discord.Embed(color=self.bot.color, title="Message Deleted", description=f"The message is too old I can't find the content", timestamp=datetime.datetime.utcnow())
            await self.send_webhook(payload.guild_id, embed, "message_delete")


    
            

def setup(bot):
    bot.add_cog(logging(bot))