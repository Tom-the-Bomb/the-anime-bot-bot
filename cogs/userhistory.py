import discord
import config
from discord import Webhook, AsyncWebhookAdapter
from discord.ext import commands
from utils.subclasses import AnimeContext
from itertools import cycle
import random
from io import BytesIO
from PIL import Image

USER_AVATAR_IMAGE_DB_GUILD_ID = 836471259344142367
USER_AVATAR_IMAGE_DB_CHANNEL_ID = 842629929039953920


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
                username="Avatar Uploder",
                avatar_url=self.bot.user.avatar_url_as(format="png"),
                file=discord.File(
                    BytesIO(await after.avatar_url_as(static_format="png").read()),
                    f"{after.id}_avatar.{'png' if not after.is_avatar_animated() else 'gif'}",
                ),
                wait=True,
            )
            await self.bot.db.execute(
                "INSERT INTO user_history (user_id, avatar_id) VALUES ($1, ARRAY [$2]) ON CONFLICT (user_id) DO UPDATE SET avatar_id = array_append (user_history.avatar_id, $2)",
                after.id,
                m.id,
            )
        elif str(before) != str(after):
            await self.bot.db.execute(
                "INSERT INTO user_history (user_id, user_names) VALUES ($1, ARRAY [$2]) ON CONFLICT (user_id) DO UPDATE SET user_names = array_append (user_history.user_names, $2)",
                after.id,
                str(after),
            )


def setup(bot):
    bot.add_cog(UserHistory(bot))
