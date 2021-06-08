from discord.ext import commands
from discord import AsyncWebhookAdapter, Webhook
from utils.subclasses import AnimeContext
import config
import prettify_exceptions
import discord

webhook_url = config.webhookurl


class ErrorSender(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx: AnimeContext, error):
        if isinstance(error, commands.CommandNotFound):
            return
        if not ctx.guild:
            server = "DM "
            name = ctx.author
        else:
            server = "Server"
            name = ctx.guild.name
        fields = [
            ["Error", error],
            ["Author", ctx.author],
            [server, name],
            ["Message", ctx.message.content],
        ]
        formater = prettify_exceptions.DefaultFormatter()
        exception = formater.format_exception(type(error), error, error.__traceback__)
        embed = discord.Embed(
            color=0xFF0000,
            title="An error occured",
            description=f"```py\n{''.join(exception)}\n```",
        )
        [embed.add_field(name=f"**{n}**", value=f"```py\n{v}```", inline=False) for n, v in fields]
        webhook = Webhook.from_url(webhook_url, adapter=AsyncWebhookAdapter(self.bot.session))
        try:
            return await webhook.send(embed=embed)
        except:
            return


def setup(bot):
    bot.add_cog(ErrorSender(bot))
