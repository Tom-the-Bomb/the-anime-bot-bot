import asyncio
import datetime
import sys
import traceback
from io import BytesIO

import aiozaneapi
import asyncdagpi
import discord
import humanize
import PIL
import prettify_exceptions
import wavelink
from discord.ext import commands, menus
from PIL import Image
from utils.subclasses import AnimeContext, GlobalCooldown, InvalidImage


class ErrorsMenuSource(menus.ListPageSource):
    def __init__(self, data):
        self.data = data
        super().__init__(data, per_page=10)

    async def format_page(self, menu, entries):
        return {
            "embed": discord.Embed(
                color=menu.ctx.bot.color, title="Errors", description="\n".join(entries)
            ).set_footer(text=f"Page {menu.current_page + 1}/{self.get_max_pages()} Total Entries: {len(self.data)}")
        }


class Error(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def embed(text):
        return discord.Embed(color=0xFF0000, title="An error occured", description=text)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: AnimeContext, error):
        if hasattr(ctx.command, "on_error"):
            return

        ignored = commands.CommandNotFound
        error = getattr(error, "original", error)
        if isinstance(error, ignored):
            return
        if isinstance(error, commands.DisabledCommand):
            embed = self.embed(f"{ctx.command} has been disabled.")
            return await ctx.send(embed=embed)
        elif isinstance(error, commands.NSFWChannelRequired):
            embed = self.embed("this command must be used in NSFW channel")
            return await ctx.send(embed=embed)
        elif isinstance(error, commands.errors.UserNotFound):
            embed = self.embed("User not found")
            return await ctx.send(embed=embed)
        elif isinstance(error, commands.errors.MemberNotFound):
            embed = self.embed("Member not found")
            return await ctx.send(embed=embed)
        elif isinstance(error, wavelink.errors.ZeroConnectedNodes):
            return await ctx.send("hmm our music system is having some problem right now")
        elif isinstance(error, asyncio.TimeoutError):
            embed = self.embed("timeout")
            return await ctx.send(embed=embed)
        elif isinstance(error, discord.errors.HTTPException):
            embed = self.embed(f"HTTPException {error.text}")
            return await ctx.send(embed=embed)
        elif isinstance(error, GlobalCooldown):
            embed = self.embed(f"You have hit the global ratelimit try again in {round(error.retry_after)} seconds")
            return await ctx.send(embed=embed)
        elif isinstance(error, PIL.UnidentifiedImageError):
            embed = self.embed("No image found")
            await ctx.reply(embed=embed)
        elif isinstance(error, InvalidImage):
            embed = self.embed(error)
            return await ctx.reply(embed=embed)
        elif isinstance(error, (Image.DecompressionBombError, Image.DecompressionBombWarning)):
            # embed = self.embed("eww decompression bomb eww stop or i use my ban hammer")
            embed = self.embed(error)
            return await ctx.reply(embed=embed)
        elif isinstance(error, aiozaneapi.GatewayError):
            embed = self.embed("Zane api error")
            await ctx.reply(embed=embed)
        elif isinstance(error, commands.errors.NotOwner):
            embed = self.embed("You must be the bot owner to use this command")
            return await ctx.send(embed=embed)
        elif isinstance(error, commands.NoPrivateMessage):
            try:
                embed = self.embed(f"{ctx.command} can not be used in Private Messages.")
                await ctx.author.send(embed=embed)
            except discord.HTTPException:
                pass
        elif isinstance(error, AttributeError):
            return
        elif isinstance(error, commands.errors.InvalidEndOfQuotedStringError):
            embed = self.embed("Make sure to put a space between the quotes")
            await ctx.send(embed=embed)
        elif isinstance(error, commands.ConversionError):
            embed = self.embed(f"Unable to convert {error.converter}")
            await ctx.send(embed=embed)
        elif isinstance(error, commands.BadArgument):
            embed = self.embed(error)
            await ctx.send(embed=embed)
        elif isinstance(error, commands.BadUnionArgument):
            embed = self.embed(error)
            await ctx.send(embed=embed)
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = self.embed(f"{error.param.name} is a required argument")
            await ctx.send(embed=embed)
        elif isinstance(error, commands.MaxConcurrencyReached):
            embed = self.embed(error)
            await ctx.send(embed=embed)
        elif isinstance(error, commands.CommandOnCooldown):
            embed = self.embed(error)
            await ctx.send(embed=embed)
        elif isinstance(error, commands.BotMissingPermissions):
            embed = self.embed(f"Bot is missing {', '.join(error.missing_perms)} to do that")
            await ctx.reply(embed=embed)
        elif isinstance(error, commands.MissingPermissions):
            embed = self.embed("you do not have permission to do that")
            await ctx.reply(embed=embed)
        elif isinstance(error, asyncdagpi.errors.BadUrl):
            embed = self.embed("You did not pass in the right arguments")
            await ctx.reply(embed=embed)
        elif isinstance(error, asyncdagpi.errors.ApiError):
            embed = self.embed("The image API have a error")
            await ctx.reply(embed=embed)
        elif isinstance(error, commands.CheckFailure):
            return
        else:
            error_id = await self.bot.db.fetchval(
                "INSERT INTO errors (error, message, created_at, author_name, command) VALUES ($1, $2, $3, $4, $5) RETURNING error_id",
                "".join(
                    prettify_exceptions.DefaultFormatter().format_exception(type(error), error, error.__traceback__)
                ),
                ctx.message.content,
                ctx.message.created_at,
                str(ctx.author),
                ctx.command.qualified_name,
            )
            embed = discord.Embed(
                color=0xFF0000,
                description=f"some weird error occured, I have told my developer to fix it, if you wish to track this error you may run `{ctx.prefix}errors track {error_id}`",
            )
            await ctx.send(embed=embed)
            # print(''.join(prettify_exceptions.DefaultFormatter().format_exception(type(error), error, error.__traceback__)))
            print("Ignoring exception in command {}:".format(ctx.command), file=sys.stderr)
            # traceback.print_exception(''.join(prettify_exceptions.DefaultFormatter().format_exception(type(error), error, error.__traceback__)))
            traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

    @commands.group(invoke_without_command=True)
    @commands.is_owner()
    async def errors(self, ctx: AnimeContext, id: int = None):
        if not id:
            errors = await self.bot.db.fetch("SELECT * FROM errors")
            if not errors:
                return await ctx.send("There are no error")
            lists = [f"{i['error_id']} - {i['command']}" for i in errors]
            pages = menus.MenuPages(source=ErrorsMenuSource(lists), delete_message_after=True)
            await pages.start(ctx)
        else:
            error = await self.bot.db.fetchrow("SELECT * FROM errors WHERE error_id = $1", id)
            upload = False
            if len(f"```py\n{error['error']}\n```") <= 2040:
                d = f"```py\n{error['error']}\n```"
            else:
                try:
                    d = await ctx.paste(error["error"])
                except KeyError:
                    d = "\u200b"
                    upload = True
            embed = discord.Embed(color=self.bot.color, description=d)
            embed.add_field(
                name="message",
                value=await ctx.paste(error["message"]) if len(error["message"]) > 1000 else error["message"],
                inline=False,
            )
            embed.add_field(
                name="created_at",
                value=humanize.naturaldelta(error["created_at"] - datetime.timedelta(hours=8)),
                inline=False,
            )
            embed.add_field(name="Author name", value=error["author_name"], inline=False)
            embed.add_field(name="command", value=error["command"], inline=False)
            if not upload:
                return await ctx.send(embed=embed)
            else:
                return await ctx.send(
                    embed=embed, file=discord.File(BytesIO(error["error"].encode("utf-8")), "error.txt")
                )

    @errors.command()
    @commands.is_owner()
    async def fix(self, ctx, id: int):
        error = await self.bot.db.fetchrow("SELECT * FROM errors WHERE error_id = $1", id)
        if not error:
            return await ctx.send("Error not found.")
        if error["trackers"]:
            for i in error["trackers"]:
                await (await self.bot.getch(i)).send(
                    f"One of the error you tracking: {id} has been fixed. Command name: {error['command']}"
                )
        await self.bot.db.execute("DELETE FROM errors WHERE error_id = $1", id)
        await ctx.send("Marked as fixed and dmed all trackers")

    @errors.command()
    async def track(self, ctx, id: int):
        """
        Track a error
        """
        r = await self.bot.db.execute("UPDATE errors SET trackers = array_append(trackers, $1) WHERE error_id = $2", ctx.author.id, id)
        if r[-1] == 0:
            return await ctx.send("Error not found.")
        await ctx.send(f"Ok, you are now tracking error {id} I will dm you if it get fixed")

    @errors.command()
    async def untrack(self, ctx, id: int):
        """
        untrack a error
        """
        r = await self.bot.db.execute("UPDATE errors SET trackers = array_remove(trackers, $1) WHERE error_id = $2", ctx.author.id, id)
        if r[-1] == 0:
            return await ctx.send("Error not found.")
        await ctx.send(f"Ok, you are no longer tracking error {id}")


def setup(bot):
    bot.add_cog(Error(bot))
