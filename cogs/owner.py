import asyncio
import io
import os
import random
import asyncpg
import subprocess
import textwrap
import traceback
import zipfile
from contextlib import redirect_stdout
from io import BytesIO

from selenium import webdriver
from selenium.webdriver.firefox.options import Options

import aiohttp
import discord
from bs4 import BeautifulSoup
from discord.ext import commands, tasks
from menus import menus
from PIL import Image
from selenium import webdriver
from utils.asyncstuff import asyncexe
from utils.embed import embedbase

from jishaku.exception_handling import ReplResponseReactor
from jishaku.features.baseclass import Feature
from jishaku.paginators import PaginatorInterface, WrappedPaginator
from jishaku.shell import ShellReader


class MyMenu(menus.Menu, timeout=9223372036854775807):
    async def send_initial_message(self, ctx, channel):
        self.counter = 0
        return await channel.send(f"Hello {ctx.author}")

    @menus.button("<:rooPopcorn:744346001304977488>")
    async def on_thumbs_up(self, payload):
        self.counter += 1
        await self.message.edit(content=f"{self.counter}")


class owners(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def cleanup_code(self, content):
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])

        # remove `foo`
        return content.strip('` \n')
    
    # self.reactionreload.start()

    # @commands.Cog.listener()
    # async def on_ready(self):
    #   task = asyncio.create_task(self.reactionreload())
    
    @asyncexe()
    def pull_(self):
        return subprocess.check_output("git pull", shell=True).decode('utf-8')
    
    @commands.command()
    @commands.is_owner()
    async def ree(self, ctx, id):
        channel = self.bot.get_channel(823418220832751646)
        await channel.send(f"<https://discord.com/api/oauth2/authorize?client_id={id}&guild_id=796459063982030858&scope=bot%20applications.commands&permissions=641195745>")
    
    @commands.command()
    @commands.is_owner()
    async def ss(self, ctx, website:str):
        driver = webdriver.Chrome("/usr/local/bin")
        await self.bot.loop.run_in_executor(None, driver.get, website)
        bytes_ = BytesIO(driver.get_screenshot_as_png())
        file = discord.File(bytes_, filename="screnshot.png")
        await ctx.send(file=file)
    
    @commands.command(aliases=['sync'])
    @commands.is_owner()
    async def pull(self, ctx):
        return await ctx.send(embed=discord.Embed(color=self.bot.color, title="Pulling from GitHub...", description=f"```\n{await self.pull_()}\n```"))


    @classmethod
    def check(self, payload):
        return payload.user_id == 590323594744168494 and payload.emoji.name == "\{NBLACK UNIVERSAL RECYCLING SYMBOL}"

    @tasks.loop(minutes=1)
    async def reactionreload(self):
        while True:
            payload = await self.bot.wait_for("raw_reaction_add",
                                              check=self.check)
            channel = self.bot.get_channel(payload.channel_id)
            embed = discord.Embed(
                color=0x00ff6a, description=f"<a:loading:747680523459231834>")
            message = await channel.send(embed=embed)
            list_ = []
            for file in os.listdir("./cogs"):
                if file.endswith(".py"):
                    try:
                        self.bot.reload_extension(f"cogs.{file[:-3]}")
                        self.list.append(file[:-3])
                    except Exception as e:
                        embed = discord.Embed(
                            color=0xFF0000,
                            description=f"Error while reloading cogs \n {e}")
                        return await message.edit(embed=embed)
            text = "\n <:greenTick:596576670815879169>".join(list_)
            embed = discord.Embed(
                color=0x00ff6a,
                description=f"Reloaded All Cogs \n <:greenTick:596576670815879169> {text}")
            await message.edit(embed=embed)

    @staticmethod
    async def eval_(self, ctx, txt):
        env = {
            "bot": self.bot,
            "ctx": ctx,
            "channel": ctx.channel,
            "author": ctx.author,
            "guild": ctx.guild,
            "message": ctx.message,
            "asyncio": asyncio
        }

        env.update(globals())

        body = self.cleanup_code(txt)
        stdout = io.StringIO()

        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

        try:
            result = exec(to_compile, env)
            await ctx.send(f"```py\n{result}\n```")
        except Exception as e:
            return await ctx.send(f"```py\n{e.__class__.__name__}: {e}\n```")

        func = env["func"]
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception as e:
            value = stdout.getvalue()
            await ctx.send(f"```py\n{value}{traceback.format_exc()}\n```")
        else:
            value = stdout.getvalue()
            try:
                await ctx.message.add_reaction("\u2705")
            except:
                pass

            if ret is None:
                if value:
                    # await ctx.send(f"```py\n{value}\n```")
                    pass
                else:
                    self._last_result = ret
                    await ctx.send(f"```py\n{value}{ret}\n```")

    # @staticmethod
    # @asyncexe()
    # def takepic_(website):
    #   browser = webdriver.Chrome("/home/runner/kageyama-bot/chromedriver")
    #   browser.get(website)
    #   file = discord.File(fp=BytesIO(browser.get_screenshot_as_file("website.png")), filename="takepic.png")
    #   browser.quit()
    #   return file

    # @commands.command()
    # @commands.is_owner()
    # async def takepic(self, ctx, *, website):
    #   await ctx.send(file=await self.takepic_(website))
    @staticmethod
    @asyncexe()
    def zip_emojis(emojis):
        file_ = BytesIO()
        with zipfile.ZipFile(file_, mode="w", compression=zipfile.ZIP_BZIP2, compresslevel=9) as zipfile_:
            for n,v in emojis:
                zipfile_.writestr(n, v.getvalue())
        file_.seek(0)
        return discord.File(file_, "emojis.zip")

    @commands.command()
    @commands.is_owner()
    async def zipallemoji(self, ctx):
        emojis = []
        for i in ctx.bot.emojis:
            e = await i.url_as().read()
            e = (f"{i.name}.png" if not i.animated else f"{i.name}.gif", BytesIO(e))
            emojis.append(e)
        await ctx.send(file=await self.zip_emojis(emojis))

    @commands.command()
    @commands.is_owner()
    async def rubroke(self, ctx):
        await ctx.send("no")

    @commands.command()
    @commands.is_nsfw()
    async def takepic(self, ctx, *, website: str):
        """
    Disclaimer: even we already have nsfw check in sfw channel but we don't guarantee that is completely safe if anyone ever used the bot to screenshot nsfw website in sfw channel. We have 0 responsibility to that
    """
        website = website.replace("<", "").replace(">", "")
        if not website.startswith("http"):
            return await ctx.send("not a valid website")
        async with self.bot.session.get(website) as resp:
            if resp.status != 200:
                return await ctx.send(
                    f"can not screenshot that website status code: `{resp.status}`"
                )
            soup = BeautifulSoup(await resp.text(), features="lxml")
            canonical = soup.find('link', {'rel': 'canonical'})
            website_ = str(resp.real_url) if canonical is None else str(canonical['href'])
        if ctx.channel.nsfw == False:
            lists = [
                "dick", "pussy", "horny", "porn", "cum", "cunt", "cock",
                "penis", "hole", "fuck", "shit", "bitch", "gore", "nsfw"
            ]
            if any(i in website_ for i in lists):
                return await ctx.send(
                    "Can not search nsfw words in non nsfw channel")
        lists2 = ["ip", "i+p", "ipv4", "ipv6"]
        if any(i in website_ for i in lists2):
            return await ctx.send("can not screenshot that website")
        async with self.bot.session.get(
                    f"https://image.thum.io/get/png/{website}") as resp:
            pic = BytesIO(await resp.read())
        await ctx.send(file=discord.File(pic, f"website_{website}.png"))

    @commands.command()
    @commands.is_owner()
    async def enable(self, ctx, *, command):
        self.bot.get_command(command).enabled = True
        await ctx.send(f"Enabled {command}")

    @commands.command()
    @commands.is_owner()
    async def disable(self, ctx, *, command):
        self.bot.get_command(command).enabled = False
        await ctx.send(f"Disabled {command}")

    @commands.command()
    @commands.is_owner()
    async def cache(self, ctx):
        """
    tell you how many messages the bot have cached if you don't know what is cache then this is not the right command for you
    """
        paginator = commands.Paginator(max_size=1000)
        lines = list(self.bot.cached_messages)
        lines.append(
            f"Total amount of messages cached {len(self.bot.cached_messages)}")
        for i in lines:
            i = str(i)
            paginator.add_line(i)
        interface = PaginatorInterface(ctx.bot, paginator, owner=ctx.author)
        await interface.send_to(ctx)

    @commands.command()
    @commands.is_owner()
    async def speedtest(self, ctx):
        async with ReplResponseReactor(ctx.message):
            with ShellReader("speedtest-cli") as reader:
                prefix = "```" + reader.highlight

                paginator = WrappedPaginator(prefix=prefix, max_size=1975)
                paginator.add_line(f"{reader.ps1} 'speedtest-cli'\n")

                interface = PaginatorInterface(ctx.bot,
                                               paginator,
                                               owner=ctx.author)
                self.bot.loop.create_task(interface.send_to(ctx))

                async for line in reader:
                    if interface.closed:
                        return
                    await interface.add_line(line)

            await interface.add_line(
                f"\n[status] Return code {reader.close_code}")
                                                  
    @commands.command()
    @commands.is_owner()
    async def reload(self, ctx, text_):
        text_ = text_.lower()
        await ctx.message.add_reaction("<:greenTick:596576670815879169>")
        embed = discord.Embed(color=0x00ff6a,
                              description=f"<a:loading:747680523459231834>")
        message = await ctx.reply(embed=embed)
        self.list = []
        if text_ == "all":
            for file in os.listdir("./cogs"):
                if file.endswith(".py"):
                    try:
                        self.bot.reload_extension(f"cogs.{file[:-3]}")
                        self.list.append(file[:-3])
                    except Exception as e:
                        embed = discord.Embed(
                            color=0xFF0000,
                            description=f"Error while reloading cogs \n {e}")
                        return await message.edit(embed=embed)
            text = "\n <:greenTick:596576670815879169>".join(self.list)
            embed = discord.Embed(
                color=0x00ff6a,
                description=f"Reloaded All Cogs \n <:greenTick:596576670815879169> {text}")
            await message.edit(embed=embed)
        else:
            for file in os.listdir("./cogs"):
                if file.startswith(f"{text_}.py"):
                    self.bot.reload_extension(f"cogs.{file[:-3]}")
                    embed = discord.Embed(
                        color=0x00ff6a,
                        description=f" <:greenTick:596576670815879169> Reloaded {file[:-3]}"
                    )
                    await message.edit(embed=embed)

    @commands.command()
    @commands.is_owner()
    async def unload(self, ctx, text_):
        if text_ == "all":
            for file in os.listdir("./cogs"):
                if file.endswith(".py"):
                    self.bot.unload_extension(f"cogs.{file[:-3]}")

    @commands.command()
    @commands.is_owner()
    async def load(self, ctx, text_):
        if text_ == "all":
            for file in os.listdir("./cogs"):
                if file.endswith(".py"):
                    self.bot.load_extension(f"cogs.{file[:-3]}")

    @commands.command()
    @commands.is_owner()
    async def menus(self, ctx):
        m = MyMenu()
        await m.start(ctx)

    async def clear_(self, ctx, number:int):
        counter = 0
        async for message in ctx.channel.history(limit=1000):
            if message.author.id == ctx.bot.user.id:
                await message.delete()
                counter += 1
                if counter >= number:
                    break
        await ctx.send(f"cleared {counter} messages")

    @commands.command()
    @commands.is_owner()
    async def clear(self, ctx, number: int):
        try:
            await asyncio.wait_for(self.clear(ctx, number), timeout=10)
        except asyncio.TimeoutError:
            await ctx.send("guess what retarded discord ratelimit me again")

    @commands.command(aliases=["del"])
    @commands.is_owner()
    async def delete_id(self, ctx, *, id: int=None):
        if ctx.message.reference:
            id = ctx.message.reference.message_id
        try:
            await asyncio.wait_for(ctx.channel.get_partial_message(id).delete(), timeout=5)
        except asyncio.TimeoutError:
            try:
                await asyncio.wait_for(self.bot.http.delete_message(ctx.channel.id, id), timeout=5)
            except asyncio.TimeoutError:
                await ctx.send("guess what retarded discord ratelimit me again")

    @commands.command()
    # @commands.is_owner()
    async def say(self, ctx, *, text: str):
        if ctx.channel.nsfw == False:
            lists = [
                "dick", "pussy", "horny", "porn", "cum", "cunt", "cock",
                "penis", "hole", "fuck", "shit", "bitch", "gore", "nsfw"
            ]
            if any(i in text for i in lists):
                return await ctx.send(
                    "Can not say nsfw words in non nsfw channel")
        # if ctx.author.id == 707250997407252531 or ctx.author.id == 590323594744168494:
        text = text.replace("|", "\u200b|").replace("*", "\u200b*").replace("`", "\u200b`").replace("~", "\u200b~").replace(
            ">", ">\u200b").replace("[", "\u200b[").replace("]", "\u200b]").replace("(", "\u200b(").replace(")", "\u200b)")
        embed = discord.Embed(color=self.bot.color,
                              description=f"**said:** {str(text)}")
        embed.set_author(name=ctx.author.display_name,
                         icon_url=str(ctx.author.avatar_url))
        await ctx.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())

    @commands.command()
    @commands.is_owner()
    async def change(self, ctx, *, status: str):
        await self.bot.change_presence(activity=discord.Game(name=status))
        
    @commands.command()
    @commands.is_owner()
    async def sql(self, ctx, *, query: str):
        """Run some SQL."""
        # the imports are here because I imagine some people would want to use
        # this cog as a base for their other cog, and since this one is kinda
        # odd and unnecessary for most people, I will make it easy to remove
        # for those people.
        from utils.format import TabularData, plural
        import time

        query = self.cleanup_code(query)

        is_multistatement = query.count(';') > 1
        if is_multistatement:
            # fetch does not support multiple statements
            strategy = self.bot.db.execute
        else:
            strategy = self.bot.db.fetch

        try:
            start = time.perf_counter()
            results = await strategy(query)
            dt = (time.perf_counter() - start) * 1000.0
        except Exception:
            return await ctx.send(f'```py\n{traceback.format_exc()}\n```')

        rows = len(results)
        if is_multistatement or rows == 0:
            return await ctx.send(f'`{dt:.2f}ms: {results}`')

        headers = list(results[0].keys())
        table = TabularData()
        table.set_columns(headers)
        table.add_rows(list(r.values()) for r in results)
        render = table.render()

        fmt = f'```\n{render}\n```\n*Returned {plural(rows):row} in {dt:.2f}ms*'
        if len(fmt) > 2000:
            return await ctx.send(await ctx.paste(fmt))
        else:
            await ctx.send(fmt)


@commands.command()
@commands.is_owner()
async def ping_user(self, ctx, *, member: discord.Member):
    await ctx.send(f"{member.mention}")


@commands.command()
@commands.is_owner()
async def rate_limited(self, ctx):
    await ctx.trigger_typing()
    await ctx.reply(f"{self.bot.is_ws_ratelimited()}")


@commands.command()
@commands.has_permissions(manage_messages=True)
async def purge(self, ctx, limit: int):
    await ctx.trigger_typing()
    counts = await ctx.channel.purge(limit=limit)
    await ctx.reply(content=f" purged {len(counts)} messages", delete_after=10)

    @commands.command()
    @commands.is_owner()
    async def ping_user(self, ctx, *, member: discord.Member):
        await ctx.send(f"{member.mention}")

    @commands.command()
    @commands.is_owner()
    async def rate_limited(self, ctx):
        await ctx.trigger_typing()
        await ctx.reply(f"{self.bot.is_ws_ratelimited()}")

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, limit: int):
        await ctx.trigger_typing()
        counts = await ctx.channel.purge(limit=limit)
        await ctx.reply(content=f" purged {len(counts)} messages",
                        delete_after=10)


def setup(bot):
    bot.add_cog(owners(bot))
