import discord
from discord.ext import commands
import datetime

class logging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.make_cache())

    async def make_cache(self):
        logs = await self.bot.db.fetch("SELECT * FROM logging")
        if logs:
            for i in logs:
                bot.logging_cache[i["guild_id"]] = dict(i.items())




    async def send_webhook(self, guild_id, embed):
        webhook_url = self.bot.logging_cache[channel.guild.id]["webhook"]
        channel_id = self.bot.logging_cache[channel.guild.id]["channel_id"]
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
        await self.send_webhook(guild_id, embed)
    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        if channel.guild.id not in self.bot.logging_cache.keys():
            return
        embed = discord.Embed(color=self.bot.color, title="Channel Updated", timestamp=channel.created_at)
        embed.set_footer(text=f"Channel ID: {channel.id}")
        return await self.send_webhook(guild_id, embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        if channel.guild.id not in self.bot.logging_cache.keys():
            return
        embed = discord.Embed(color=self.bot.color, title="Channel Deleted", description=f"**channel name:** {channel.name}\n**Category:** {channel.category}", timestamp=channel.created_at)
        embed.set_footer(text=f"Channel ID: {channel.id}")
        await self.send_webhook(guild_id, embed)
    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        if role.guild.id not in self.bot.logging_cache.keys():
            return
        embed = discord.Embed(color=self.bot.color, title="Role Created", description=f"**Role name:** {role.name}\n**Color:** {str(channel.color)}", timestamp=channel.created_at)
        embed.set_footer(text=f"Channel ID: {channel.id}")
        await self.send_webhook(guild_id, embed)


    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        ...
    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        if role.guild.id not in self.bot.logging_cache.keys():
            return
        embed = discord.Embed(color=self.bot.color, title="Role Deleted", description=f"**Role name:** {role.name}\n**Color:** {str(channel.color)}", timestamp=channel.created_at)
        embed.set_footer(text=f"Channel ID: {channel.id}")
        await self.send_webhook(guild_id, embed)
    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        ...
    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild, before, after):
        ...
    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        ...
    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        ...
    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        ...
    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        ...
    @commands.Cog.listener()
    async def on_invite_delete(self, invite):
        ...
    @commands.Cog.listener()
    async def on_member_join(self, member):
        ...
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        ...
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if not before.channel:
            embed = discord.Embed(color=self.bot.color, )
    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload):
        if payload.cached_message:
            return
        embed = discord.Embed(color=self.bot.color, title="Message Edited", description=f"The message is too old I can't find the content", timestamp=datetime.datetime.utcnow())
        await self.send_webhook(guild_id, embed)
    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        before_content = before.content or  "message don't have content could be a attachment or embed"
        after_content = before.content or  "message don't have content could be a attachment or embed"
        embed = discord.Embed(color=self.bot.color, title="Message Deleted", timestamp=datetime.datetime.utcnow())
        embed.add_field(name="Before", value=f"**Content:** {before_content}")
        embed.add_field(name="After", value=f"**Content:** {after_content}")
        await self.send_webhook(guild_id, embed)
    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload):
        ids = "\n".join(payload.message_ids)
        embed = discord.Embed(color=self.bot.color, title="Bulk messages deleted", description=f"Message Ids: \n{ids}")
        await self.send_webhook(payload.guild_id, embed)
    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):
        if message.webhook_id:
            return
        message = payload.cached_message
        if message:
            content = message.content or  "message don't have content could be a attachment or embed"
            embed = discord.Embed(color=self.bot.color, title="Message Deleted", description=f"**Content:** {content}", timestamp=datetime.datetime.utcnow())
            await self.send_webhook(guild_id, embed)
        else:
            embed = discord.Embed(color=self.bot.color, title="Message Deleted", description=f"The message is too old I can't find the content", timestamp=datetime.datetime.utcnow())
            await self.send_webhook(guild_id, embed)


    
            

def setup(bot):
    bot.add_cog(logging(bot))