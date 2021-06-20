import discord
from discord.ext import commands
import itertools
from utils.asyncstuff import asyncexe


class utils:
    @staticmethod
    @asyncexe()
    def all_possible_caps(text):
        return list(map("".join, itertools.product(*((c.upper(), c.lower()) for c in text))))

    async def get_pic(self, ctx):
        msg = ctx.message
        if not msg.reference:
            return False
        if msg.reference.cached_message:
            if msg.reference.cached_message.attachments:
                return msg.reference.cached_message.attachments[0].url
            if (
                msg.reference.cached_message.embeds
                and msg.reference.cached_message.embeds[0].url
                and msg.reference.cached_message.embeds[0].type == "image"
            ):
                return msg.reference.cached_message.embeds[0].url
        else:
            if msg.reference.message_id and msg.reference.channel_id:
                msg = await ctx.bot.get_channel(msg.reference.channel_id).fetch_message(msg.reference.message_id)
                if msg.attachments:
                    return msg.attachments[0].url
                if msg.embeds and msg.embeds[0].url and msg.embeds[0].type == "image":
                    return msg.embeds[0].url

        return False
