import discord
import config
import typing
from discord import Webhook, AsyncWebhookAdapter
from discord.ext import commands, menus
from utils.subclasses import AnimeContext
from math import ceil, floor
from itertools import cycle
import random
from io import BytesIO
from PIL import Image

USER_AVATAR_IMAGE_DB_GUILD_ID = 836471259344142367
USER_AVATAR_IMAGE_DB_CHANNEL_ID = 842629929039953920

class AvatarMenuSource(menus.ListPageSource):
    def __init__(self, data, user):
        self.user = user
        self.data = data
        super().__init__(data, per_page=1)

    async def format_page(self, menu, entries):
        return {
            "embed": discord.Embed(
                color=menu.ctx.bot.color,
                title=f"{self.user}'s avatars"
            ).set_image(url=entries).set_footer(text=f"Page {menu.current_page + 1}/{self.get_max_pages()} Total Entries: {len(self.data)}")
        }

class UserHistory(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.UPLOADERS = cycle(
            [
                Webhook.from_url(config.avatar_uploader_1, adapter=AsyncWebhookAdapter(self.bot.session)),
                Webhook.from_url(config.avatar_uploader_2, adapter=AsyncWebhookAdapter(self.bot.session)),
                Webhook.from_url(config.avatar_uploader_3, adapter=AsyncWebhookAdapter(self.bot.session)),
                Webhook.from_url(config.avatar_uploader_4, adapter=AsyncWebhookAdapter(self.bot.session)),
                Webhook.from_url(config.avatar_uploader_5, adapter=AsyncWebhookAdapter(self.bot.session)),
                Webhook.from_url(config.avatar_uploader_6, adapter=AsyncWebhookAdapter(self.bot.session)),
                Webhook.from_url(config.avatar_uploader_7, adapter=AsyncWebhookAdapter(self.bot.session)),
                Webhook.from_url(config.avatar_uploader_8, adapter=AsyncWebhookAdapter(self.bot.session)),
                Webhook.from_url(config.avatar_uploader_9, adapter=AsyncWebhookAdapter(self.bot.session)),
                Webhook.from_url(config.avatar_uploader_10, adapter=AsyncWebhookAdapter(self.bot.session)),
            ]
        )

    @commands.Cog.listener()
    async def on_user_update(self, before, after):
        if before.avatar_url_as(static_format="png") != after.avatar_url_as(static_format="png"):
            m = await next(self.UPLOADERS).send(
                after.id,
                username="Avatar Uploader",
                avatar_url=self.bot.user.avatar_url_as(format="png"),
                file=discord.File(
                    BytesIO(await after.avatar_url_as(static_format="png").read()),
                    f"{after.id}_avatar.{'png' if not after.is_avatar_animated() else 'gif'}",
                ),
                wait=True,
            )
            await self.bot.db.execute(
                "INSERT INTO user_history (user_id, avatar_url) VALUES ($1, ARRAY [$2]) ON CONFLICT (user_id) DO UPDATE SET avatar_url = array_append (user_history.avatar_url, $2)",
                after.id,
                m.attachments[0].url,
            )
        elif str(before) != str(after):
            await self.bot.db.execute(
                "INSERT INTO user_history (user_id, user_names) VALUES ($1, ARRAY [$2]) ON CONFLICT (user_id) DO UPDATE SET user_names = array_append (user_history.user_names, $2)",
                after.id,
                str(after),
            )
    
    @commands.command()
    async def avatars(self, ctx, *, member: typing.Union[discord.Member, discord.User]=None):
        member = member or ctx.author
        avatars = await self.bot.db.fetchval("SELECT avatar_url FROM user_history WHERE user_id = $1", member.id)
        if not avatars:
            return await ctx.send(f"We can't find any past avatars for {str(member)} in our database, try again later.")
        pages = menus.MenuPages(source=AvatarMenuSource(avatars, user=member), delete_message_after=True)
        await pages.start(ctx)

    @commands.command()
    async def usernames(self, ctx, *, member: typing.Union[discord.Member, discord.User]=None):
        """
        Show you the member's past usernames
        """
        member = member or ctx.author
        user_names = await self.bot.db.fetchval("SELECT user_names FROM user_history WHERE user_id = $1", member.id)
        if not user_names:
            return await ctx.send(f"We can't find any past usernames for {str(member)} in our database, try again later.")
        final = ", ".join(
            discord.utils.escape_mentions(discord.utils.escape_markdown(i))
            for i in user_names
        )
        await ctx.send(f"{str(member)}'s past usernames: {final}")
def setup(bot):
    bot.add_cog(UserHistory(bot))
