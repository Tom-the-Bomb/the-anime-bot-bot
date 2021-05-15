import discord
from discord.ext import commands
from utils.subclasses import AnimeContext
import copy
import datetime


class Custom(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild.id == 786359602241470464:
            if member.bot:
                await member.add_roles(discord.Object(786369068834750466))
            else:
                await member.add_roles(discord.Object(792645158495453204))
        if member.guild.id == 796459063982030858 and member.bot:
            await member.add_roles(discord.Object(833132759361912842))


def setup(bot):
    bot.add_cog(Custom(bot))
