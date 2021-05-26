import discord
from discord.ext import commands, menus
import prettify_exceptions
import humanize
from utils.subclasses import GlobalCooldown
from utils.subclasses import AnimeContext
import PIL
import asyncio
import aiozaneapi
import asyncdagpi

class ErrorsMenuSource(menus.ListPageSource):
    def __init__(self, data):
        self.data = data
        super().__init__(data, per_page=10)

    async def format_page(self, menu, entries):
        return {
            "embed": discord.Embed(color=menu.ctx.bot.color, title=f"Errors", description="\n".join(entries)).set_footer(text=f"Page {menu.current_page + 1}/{self.get_max_pages()} Total Entries: {len(self.data)}")
        }

class Error(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    def embed(self, text):
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
        elif isinstance(error, discord.errors.Forbidden):
            embed = self.embed(error.text)
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
        elif isinstance(error, Image.DecompressionBombError):
            embed = self.embed("eww decompression bomb eww stop or i use my ban hammer")
            await ctx.reply(embed=embed)
        elif isinstance(error, aiozaneapi.GatewayError):
            embed = self.embed("Zane api error")
            await ctx.reply(embed=embed)
        elif isinstance(error, commands.errors.NotOwner):
            embed = self.embed("You must be the bot owner to use this command")
            return await ctx.send(embed=embed)
        elif isinstance(error, commands.NoPrivateMessage):
            try:
                embed = self.embed("{ctx.command} can not be used in Private Messages.")
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
            embed = self.embed(f"Unable to convert")
            await ctx.send(embed=embed)
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = self.embed(f"You are missing `{error.param.name}` argument")
            await ctx.send(embed=embed)
        elif isinstance(error, commands.MaxConcurrencyReached):
            return
        elif isinstance(error, commands.CommandOnCooldown):
            return
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
                description=f"some weird error occured, I have told my developer to fix it, if you wish to track this error you may run `{ctx.prefix}errors track {error_id}`"
            )
            await ctx.send(embed=embed)
            # print(''.join(prettify_exceptions.DefaultFormatter().format_exception(type(error), error, error.__traceback__)))
            print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
            # traceback.print_exception(''.join(prettify_exceptions.DefaultFormatter().format_exception(type(error), error, error.__traceback__)))
            traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
    
    @commands.command()
    async def texterror(self, ctx):
        ...
    
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
            embed = discord.Embed(
                color=self.bot.color,
                description=f"```py\n{error['error']}\n```"
                if len(f"```py\n{error['error']}\n```") <= 2048
                else await ctx.paste(error["error"]),
            )
            embed.add_field(name="message", value=error["message"], inline=False)
            embed.add_field(
                name="created_at",
                value=humanize.naturaldelta(error["created_at"] - datetime.timedelta(hours=8)),
                inline=False
            )
            embed.add_field(name="Author name", value=error["author_name"], inline=False)
            embed.add_field(name="command", value=error["command"], inline=False)

            return await ctx.send(embed=embed)
    
    @errors.command()
    async def fix(self, ctx, id:int):
        error = await self.bot.row("SELECT * FROM errors WHERE error_id = $1", ctx.author.id)
        for i in error["trackers"]:
            await (await self.bot.getch(i)).send(f"One of the error you tracking: {id} has been fixed. Command name: {error['command']}")
        await ctx.send("Marked as fixed and dmed all trackers")
    
    @errors.command()
    async def track(self, ctx, id: int):
        """
        Track a error
        """
        await self.bot.db.execute("UPDATE errors SET trackers = array_append(trackers, $1)", ctx.author.id)
        await ctx.send(f"Ok, you are now tracking error {id} I will dm you if it get fixed")
    
    @errors.command()
    async def untrack(self, ctx, id: int):
        """
        untrack a error
        """
        await self.bot.db.execute("UPDATE errors SET trackers = array_remove(trackers, $1)", ctx.author.id)
        await ctx.send(f"Ok, you are no longer tracking error {id}")

def setup(bot):
    bot.add_cog(Error(bot))